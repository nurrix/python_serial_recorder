
import serial
import serial.tools.list_ports
import threading
import queue
import time
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from controller import SerialController  # Only imported for type hinting



class SerialModel:
    def __init__(self):
        self.serial_connection: Optional[serial.Serial] = None
        self.data_queue = queue.Queue()  # Thread-safe queue for data communication
        self.read_thread = None
        self.is_reading = False


    def open_connection(self, port: str, baudrate: int) -> tuple[bool, Optional[str]]:
        """Open a serial connection and start reading in a separate thread."""
        if self.serial_connection and self.serial_connection.is_open:
            raise serial.SerialException("Already connected to a serial port.")

        try:
            self.serial_connection = serial.Serial(port, baudrate)
            self.is_reading = True
            self.read_thread = threading.Thread(target=self.read_from_serial)
            self.read_thread.start()
        except serial.SerialException as e:
            raise serial.SerialException(f"Error opening serial port: {str(e)}")

    def read_from_serial(self):
        """Continuously read data from the serial port in a background thread."""
        while self.is_reading:
            if self.serial_connection and self.serial_connection.is_open:
                try:
                    data = self.serial_connection.readline().decode('ascii').strip()
                    if data:
                        self.data_queue.put(data)  # Put data in the queue to be processed in the main thread
                except serial.SerialException as e:
                    raise serial.SerialException(f"Error reading from serial port: {str(e)}")
            time.sleep(0.1)  # Sleep briefly to avoid busy-waiting and consuming too much CPU

    def close_connection(self) -> None:
        """Close the serial connection."""
        if self.serial_connection and self.serial_connection.is_open:
            self.is_reading = False  # Stop the reading thread
            self.read_thread.join()  # Wait for the read thread to finish
            self.serial_connection.close()

    def get_data_from_queue(self) -> Optional[str]:
        """Get data from the queue for the main thread."""
        if not self.data_queue.empty():
            return self.data_queue.get_nowait()
        return None

    def get_available_ports(self) -> list[str]:
        """Get the list of available COM ports."""
        try:
            ports = [port.device for port in serial.tools.list_ports.comports()]
            if not ports:
                raise serial.SerialException("No available COM ports found.")
            return sorted(list(set(ports)))
        except serial.SerialException as e:
            raise e  # Raise the exception to be handled in the controller/view