import serial
from typing import TYPE_CHECKING, Optional, Type

if TYPE_CHECKING:
    from models import SerialModel
    from views import SerialApp

class SerialController:
    def __init__(self, model: "SerialModel", view: "SerialApp"):
        self.serial_connection: Optional[serial.Serial] = None
        self.model = model
        self.view = view
        
        self.view.after(100, self.__waiting_for_port_selection)

    def __waiting_for_port_selection(self) -> None:
        if self.serial_connection:
            return
        
        self.check_ports()
        
        self.view.after(100, self.__waiting_for_port_selection)
        

    def check_ports(self) -> list[str]:
        """Get the list of available COM ports."""
        available_ports = self.model.get_available_ports()              
        self.view.update_ports(available_ports)
        

    def open_connection(self, port: str, baudrate: int, fs:int, duration:int) -> tuple[bool, Optional[str]]:
        """Open a serial connection."""
        if self.serial_connection and self.serial_connection.is_open:
            return False, "Already connected."
        
        try:
            self.serial_connection = serial.Serial(port, baudrate)
            return True, None
        except serial.SerialException as e:
            return False, str(e)

    def read_data(self) -> Optional[str]:
        """Read data from the serial port."""
        if self.serial_connection and self.serial_connection.is_open:
            try:
                data = self.serial_connection.readline().decode('ascii').strip()
                return data
            except Exception as e:
                return None
        return None

    def close_connection(self) -> None:
        """Close the serial connection."""
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
