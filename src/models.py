import serial
import serial.tools.list_ports as list_ports
import threading
import time
from typing import Optional
import pandas as pd
import numpy as np

import logging

logger = logging.getLogger(__name__)


def calculate_2D_matrix(data) -> tuple[int, int]:
    """ Calculate the number of rows and columns in a 2D matrix."""
    num_rows: int = len(data)
    if num_rows == 0:
        num_cols = 0
    else:
        num_cols = len(data[0])
    return num_rows, num_cols


def str_contains_only_numbers(row: str):
    """ Check if a string contains only numbers and spaces."""
    return row and all(c.isdigit() or c == " " for c in row)


def str_to_intarray(data: str):
    """ Convert a string of numbers separated by spaces to a list of integers."""
    return list(map(int, data.split(" ")))


class Model:
    """ Model class for the MVC pattern."""
    def __init__(self):
        """ Initialize the model."""
        self.serial_connection: Optional[serial.Serial] = None
        self.read_thread: Optional[threading.Thread] = None
        self.is_reading = False
        self.SAMPLES_PER_CHANNEL: int | None = None
        self.__buffer = pd.DataFrame()
        self.__df_update_lock = threading.Lock()

    def open_connection(
        self,
        port: str,
        baudrate: int,
        samples_per_channel: int,
    ) -> tuple[bool, Optional[str]]:
        """Open a serial connection and start reading in a separate thread."""
        if self.is_connected:
            raise serial.SerialException("Already connected to a serial port.")

        try:
            self.serial_connection = serial.Serial(port, baudrate)
            self.SAMPLES_PER_CHANNEL = samples_per_channel
            self.read_thread = threading.Thread(
                target=self.start_continuous_read_from_serial,
                name="SerialReader",
                daemon=True,
            )

            self.read_thread.start()

        except serial.SerialException as e:
            raise serial.SerialException(f"Error opening serial port: {str(e)}")

    def start_continuous_read_from_serial(self, updaterate_sec: float = 1 / 50):
        """Continuously read data from the serial port in a background thread."""
        # write to esp32, that it needs to write data
        self.read(flag=True)
        rest: str = ""
        counter: int = 0
        while self.is_connected:
            try:
                available_bytes: int = self.serial_connection.in_waiting
            except Exception:
                available_bytes = 0

            if available_bytes == 0:
                time.sleep(updaterate_sec)
                continue
            # read n available bytes from serial connection (bytes)
            ascii_data: str = rest + self.serial_connection.read(available_bytes).decode()
            # Seperate each row of data
            row_asci_data: list[str] = ascii_data.split("\r\n")
            rest: str = row_asci_data[-1]
            if len(row_asci_data) < 2:
                continue  # If there are less than 2 rows, skip rest

            data: list[str] = row_asci_data[:-2]
            # remove rows where there are non-numeric data, split by " ", and convert to int
            data_filtered: list[str] = filter(str_contains_only_numbers, data)
            data_integers: list[list[int]] = list(map(str_to_intarray, data_filtered))

            # get number of rows and channels in new data
            num_rows, num_channels = calculate_2D_matrix(data_integers)
            if num_rows == 0 or num_channels == 0:
                # If there are no rows, or no columns, skip rest
                continue

            # create a dataframe with the new data
            column_names: list[str] = [f"Ch{i}" for i in range(num_channels)]
            dfnew = pd.DataFrame(
                data_integers,
                index=range(counter, counter + num_rows),
                columns=column_names,
            )
            self.update_df(data=dfnew)
            counter += num_rows
            # Sleep for a short duration
            time.sleep(updaterate_sec)

    def update_df(self, data: pd.DataFrame) -> None:
        """Update the buffer with new data."""
        with self.__df_update_lock:
            if self.__buffer.shape[1] != data.shape[1]:
                # If the number of columns of the df has changed, reinitialize the dataframe
                sz = (self.SAMPLES_PER_CHANNEL, data.shape[1])
                self.__buffer = pd.DataFrame(
                    np.zeros(sz), columns=data.columns, index=range(-self.SAMPLES_PER_CHANNEL, 0), dtype=int
                )
            # Append new data to buffer
            self.__buffer: pd.DataFrame = pd.concat([self.__buffer, data], ignore_index=False)

            # If the buffer is larger than the specified number of samples, remove the oldest samples
            if len(self.__buffer) > self.SAMPLES_PER_CHANNEL:
                self.__buffer: pd.DataFrame = self.__buffer.iloc[-self.SAMPLES_PER_CHANNEL :]

    def close_connection(self) -> None:
        """Close the serial connection."""
        if self.is_connected:
            self.read(False)
            self.serial_connection.close()
            logger.info("Closed connection")

    def get_available_ports(self) -> list[str]:
        """Get the list of available COM ports."""
        ports: list[str] = [port.device for port in list_ports.comports()]
        if not ports:
            return []
        return sorted(list(set(ports)))

    def read(self, flag: bool) -> None:
        """write a byte ('s' or 'e') to com-port, depending on flag"""
        self.is_reading = flag and self.is_connected
        if self.is_disconnected:
            logger.error("No established Connection >> Cant start/stop reading")
            return

        # write 's' or 'e' to com-port
        msg = b"s" if flag else b"e"
        try:
            self.serial_connection.write(msg)
        except serial.SerialException as e:
            logger.error(str(e))

    def update_snapshot(self) -> None:
        """copy current buffer into a snapshot"""
        with self.__df_update_lock:
            self.__snapshot: pd.DataFrame = self.__buffer.copy()

    def get_snapshot(self, is_frozen: bool) -> pd.DataFrame | None:
        """Return a snapshot of the data or the buffer.
        If is_frozen is True, return a snapshot, else return the buffer.
        """
        if not self.is_reading:
            return None

        with self.__df_update_lock:
            if is_frozen:
                return self.__snapshot.copy()
            return self.__buffer.copy()

    @property
    def is_connected(self) -> bool:
        """Return True if serial is connected to COM port"""
        return self.serial_connection and self.serial_connection.is_open and self.read_thread.is_alive
    
    @property
    def is_disconnected(self) -> bool:
        """Return True if serial is connected to COM port is not connected"""
        return not self.is_connected

    def __del__(self) -> None:
        """destructor"""
        self.close_connection()
