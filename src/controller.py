import threading
import time
import pandas as pd
import serial
from typing import TYPE_CHECKING, Optional
import logging
import weakref

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from models import SerialModel
    from views import SerialApp

class SerialController:
    def __init__(self, serial_model: "SerialModel", view: "SerialApp"):
        self.serial_model = serial_model
        self.view = view
        
        self.view.after(100, self.waiting_for_port_selection)
        self.current_data: pd.DataFrame = pd.DataFrame()
        
        threading.Thread(target=self.update_lines, name="Line Updater", daemon=True).start()
        

    def waiting_for_port_selection(self) -> None:
        if self.serial_model.is_connected:
            return
        
        self.check_ports()
        
        self.view.after(100, self.waiting_for_port_selection)
        

    def check_ports(self) -> list[str]:
        """Get the list of available COM ports."""
        available_ports = self.serial_model.get_available_ports()              
        self.view.update_ports(available_ports)
        

    def open_connection(self, port: str, baudrate: int, fs:int, duration:int) -> tuple[bool, Optional[str]]:
        """Open a serial connection."""
        
        try:
            L = fs * duration
            self.serial_model.open_connection(port=port, baudrate=baudrate,L=L)
            self.L:int = int(fs * duration)
        except serial.SerialException as e:
            logger.error(str(e))
            return False, str(e)
        return True, None

    
    def update_lines(self,dt=0.1):
        while self.view:
            df = self.serial_model.shapshot
            if len(df):
                self.view.after(0, lambda: self.view.display_data(data=df)) 
            
            time.sleep(dt)
            
        


    def close_connection(self) -> None:
        """Close the serial connection."""
        self.serial_model.close_connection()
        
