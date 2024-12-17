import threading
import time
from tkinter import filedialog
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
        self.is_frozen = False
        self.view.after(100, self.waiting_for_port_selection)
        self.current_data: pd.DataFrame = pd.DataFrame()

        threading.Thread(
            target=self.update_lines, name="Line Updater", daemon=True
        ).start()

    def waiting_for_port_selection(self) -> None:
        if self.serial_model.is_connected:
            return

        self.check_ports()

        self.view.after(100, self.waiting_for_port_selection)

    def check_ports(self) -> list[str]:
        """Get the list of available COM ports."""
        available_ports = self.serial_model.get_available_ports()
        self.view.update_ports(available_ports)

    def open_connection(
        self, port: str, baudrate: int, samples_per_channel: int
    ) -> tuple[bool, Optional[str]]:
        """Open a serial connection."""

        try:
            self.serial_model.open_connection(
                port=port, baudrate=baudrate, samples_per_channel=samples_per_channel
            )
            self.SAMPLES_PER_CHANNEL: int = int(samples_per_channel)
        except serial.SerialException as e:
            logger.error(str(e))
            return False, str(e)

        self.view.after(0, self.view.disable_buttons)
        return True, None

    def update_lines(self, dt=0.1):
        while self.view:
            df = self.serial_model.get_snapshot(is_frozen=self.is_frozen)
            if not df.empty:
                self.view.after(0, lambda: self.view.display_data(data=df))

            time.sleep(dt)

    def snapshot_show(self):
        """either freeze or resume visualization"""
        self.is_frozen = not self.is_frozen

        if self.is_frozen:
            logger.info("Freeze image")
            self.serial_model.set_snapshot()
        else:
            logger.info("UnfFreeze image")

    def save_snapshot(self):
        if not self.is_frozen:
            self.snapshot_show()
            self.view.after(0, self.save_snapshot)
            return

        df = self.serial_model.get_snapshot(self.is_frozen)

        if df.empty:
            # If dataframe is empty, restart recording, and cancel save
            logger.info("Nothing to save, unfreezing.")
            self.snapshot_show()
            return

        # Open file dialog to prompt user for a location and file name
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[
                ("Excel files", "*.xlsx"),
                ("CSV files", "*.csv"),
                ("JSON files", "*.json"),
                ("All files", "*.*"),
            ],
            title="Save Timeseries",
        )

        if file_path.endswith(".csv"):
            df.to_csv(file_path, index=True)
            logger.info(f"Data saved as CSV to {file_path}")

        # Save as Excel
        elif file_path.endswith(".xlsx"):
            df.to_excel(file_path, index=True)
            logger.info(f"Data saved as Excel to {file_path}")

        # Save as JSON
        elif file_path.endswith(".json"):
            df.to_json(file_path, orient="records", lines=True)
            logger.info(f"Data saved as JSON to {file_path}")

    def close_connection(self) -> None:
        """Close the serial connection."""
        self.serial_model.close_connection()
