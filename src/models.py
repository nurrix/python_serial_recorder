import serial
import serial.tools.list_ports
import threading
import time
from typing import Optional
import pandas as pd
import numpy as np


import logging

logger = logging.getLogger(__name__)


def row_col_count(data) -> tuple[int, int]:
    num_rows: int = len(data)
    if num_rows == 0:
        num_cols = 0
    else:
        num_cols = len(data[0])
    return num_rows, num_cols


def contains_only_numbers(row):
    # Keep only rows where each character is either a number or a space
    return row and all(c.isdigit() or c == " " for c in row)


def convert_to_numbers(data: str):
    # converts string to integers
    return list(map(int, data.split(" ")))


class Model:
    def __init__(self):
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

        logger.info(f"Opened serial connection port:{port}, baudrate:{baudrate}")

    def start_continuous_read_from_serial(self, updaterate_sec: float = 1 / 50):
        """Continuously read data from the serial port in a background thread."""
        # write to esp32, that it needs to write data
        self.on_read(flag=True)
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
            ascii_data: str = (
                rest + self.serial_connection.read(available_bytes).decode()
            )
            # Seperate each row of data
            row_asci_data: list[str] = ascii_data.split("\r\n")
            rest: str = row_asci_data[-1]
            if len(row_asci_data) < 2:
                continue

            data: list[str] = row_asci_data[:-2]
            # remove rows where there are non-numeric data, split by " ", and convert to int
            data_filtered: list[str] = filter(contains_only_numbers, data)
            data_integers: list[list[int]] = list(
                map(convert_to_numbers, data_filtered)
            )

            # get number of rows and channels in new data
            num_rows, num_channels = row_col_count(data_integers)
            if num_rows == 0 or num_channels == 0:
                # If there are no rows, or no columns, skip rest
                continue

            # create a dataframe with the new data
            column_names: list[str] = [f"Ch{i}" for i in range(num_channels)]
            dfnew = pd.DataFrame(
                data_integers,
                columns=column_names,
                index=range(counter, counter + num_rows),
            )
            self.update_df(data=dfnew)
            counter += num_rows
            # Sleep for a short duration
            time.sleep(updaterate_sec)

    def update_df(self, data: pd.DataFrame) -> None:
        """append new data to buffer"""
        with self.__df_update_lock:
            if self.__buffer.shape[1] != data.shape[1]:
                # If the number of columns of the df has changed, reinitialize the dataframe
                logger.debug("Resizing buffer")
                self.__buffer = pd.DataFrame(
                    np.zeros([self.SAMPLES_PER_CHANNEL, data.shape[1]], dtype=int),
                    columns=data.columns,
                )
            # Append new data to buffer
            self.__buffer: pd.DataFrame = pd.concat(
                [self.__buffer, data], ignore_index=True
            )

            # Drop rows with the smallest indices
            index = self.__buffer.index[: -self.SAMPLES_PER_CHANNEL]
            self.__buffer.drop(index=index, inplace=True)
            self.__buffer.reset_index(drop=True, inplace=True)

    def close_connection(self) -> None:
        """Close the serial connection."""
        if self.is_connected:
            self.on_read(False)
            self.serial_connection.close()
            logger.info("Closed connection")
            self.read_thread.join()  # Wait for the read thread to finish
            logger.info("joined connection")

    def get_available_ports(self) -> list[str]:
        """Get the list of available COM ports."""
        try:
            ports: list[str] = [
                port.device for port in serial.tools.list_ports.comports()
            ]
            if not ports:
                return []
            return sorted(list(set(ports)))
        except serial.SerialException as e:
            raise e  # Raise the exception to be handled in the controller/view

    def on_read(self, flag: bool) -> None:
        """write a byte ('s' or 'e') to com-port, depending on flag"""
        if not self.is_connected:
            self.is_reading: bool = False
            logger.error("No established Connection >> Cant start reading")
            return

        self.is_reading = flag
        # write 's' or 'e' to com-port
        msg = b"s" if flag else b"e"
        try:
            self.serial_connection.write(msg)
        except serial.SerialException as e:
            logger.error(str(e))

    def set_snapshot(self) -> None:
        """copy current buffer into a snapshot"""
        with self.__df_update_lock:
            self.__snapshot: pd.DataFrame = self.__buffer.copy()

    def get_snapshot(self, is_frozen: bool) -> pd.DataFrame:
        with self.__df_update_lock:
            if is_frozen:
                return self.__snapshot.copy()
            return self.__buffer.copy()

    @property
    def is_connected(self) -> bool:
        """Return True if serial is connected to COM port"""
        return (
            self.serial_connection
            and self.serial_connection.is_open
            and self.read_thread.is_alive
        )

    def __del__(self) -> None:
        """destructor"""
        self.close_connection()
