
import numpy as np
import serial
import serial.tools.list_ports
import threading
import time
from typing import Optional
import pandas as pd


import logging

logger = logging.getLogger(__name__)


def contains_only_numbers(row):
    # Keep only rows where each character is either a number or a space
    return  row and all(c.isdigit() or c == ' ' for c in row)

def convert_to_numbers(data:str):
    # converts string to integers
    return list(map(int, data.split(" ")))

class SerialModel:
    def __init__(self):
        self.serial_connection: Optional[serial.Serial] = None
        self.read_thread = None
        self.is_reading = False
        self.L = None
        self.df = pd.DataFrame()
        self.__df_update_lock = threading.Lock()

    def open_connection(self, port: str, baudrate: int, L:int, ) -> tuple[bool, Optional[str]]:
        """Open a serial connection and start reading in a separate thread."""
        if self.is_connected:
            
            raise serial.SerialException("Already connected to a serial port.")

        try:
            self.serial_connection = serial.Serial(port, baudrate)
            self.L = L
            self.read_thread = threading.Thread(target=self.start_continuous_read_from_serial, name="SerialReader")
            
            self.read_thread.start()
            
        except serial.SerialException as e:
            
            raise serial.SerialException(f"Error opening serial port: {str(e)}")
        
        logger.info(f"Opened serial connection port:{port}, baudrate:{baudrate}")

    def start_continuous_read_from_serial(self, updaterate_sec:float = 2**-6):
        """Continuously read data from the serial port in a background thread."""
        logger.info("Started Continuous read from serialport")
        
        if updaterate_sec<=0.0:
            raise serial.SerialException(f"Error: updaterate should be a possitive number")
        self.on_read(flag = True)
        rest = ''
        counter = 0
        while self.is_connected:
            available_bytes = self.serial_connection.in_waiting
            if available_bytes:
                # read n available bytes from serial connection (bytes)
                ascii_data = rest + self.serial_connection.read(available_bytes).decode()
                # Seperate each row of data
                row_asci_data = ascii_data.split("\r\n")
                rest = row_asci_data[-1]
                data_to_analyze = row_asci_data[:-2]
                # remove rows where there are non-numeric data, split by " ", and convert to int
                new_data = filter(contains_only_numbers, data_to_analyze)
                data_integers = list(map(convert_to_numbers,new_data))
                
                num_rows = len(data_integers)
                num_channels = len(data_integers[0])
                
                
                column_names = [f"Ch{i}" for i in range(num_channels)]
                dfnew = pd.DataFrame(data_integers,columns=column_names,index=range(counter, counter+num_rows))
                counter += num_rows
                self.update_df(df2=dfnew)
                
            time.sleep(updaterate_sec)

    def close_connection(self) -> None:
        """Close the serial connection."""
        if self.is_connected:
            
            self.on_read(False)
            self.serial_connection.close()
            self.read_thread.join()  # Wait for the read thread to finish


    def get_available_ports(self) -> list[str]:
        """Get the list of available COM ports."""
        try:
            ports = [port.device for port in serial.tools.list_ports.comports()]
            if not ports:
                raise serial.SerialException("No available COM ports found.")
            return sorted(list(set(ports)))
        except serial.SerialException as e:
            raise e  # Raise the exception to be handled in the controller/view
    
    def on_read(self, flag: bool):
        if not self.is_connected:
            self.is_reading = flag
            logger.error("No established Connection >> Cant start reading")
            
        self.is_reading = flag
            
        if self.is_reading:
            self.serial_connection.write(b"s")
        else:
            self.serial_connection.write(b"e")
            
    def update_df(self, df2: pd.DataFrame):
        with self.__df_update_lock:
            if self.df.shape[1] != df2.shape[1]:
                logger.info("Resetting size of df")
                self.df = pd.DataFrame(0,columns=df2.columns,index=range(df2.index[0]-1,df2.index[0]-self.L))
            self.df = pd.concat([self.df, df2])
            
            # If the DataFrame's length exceeds L, drop the rows with the lowest indices
            if len(self.df) > self.L:
                # Drop rows with the smallest indices
                self.df = self.df.loc[self.df.index[-self.L:]]
            
            
        
    @property
    def shapshot(self) -> pd.DataFrame | None:
        with self.__df_update_lock:
            df = self.df.copy()
        return df
    
    @property
    def is_connected(self):
        if self.serial_connection and self.serial_connection.is_open and self.read_thread.is_alive:
            return True
        return False
    
    
    def __del__(self):
        logger.debug("Destroying...")
        self.close_connection()
        