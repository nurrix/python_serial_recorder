from tkinter import filedialog
from pandas import DataFrame
import serial
from typing import TYPE_CHECKING
import logging

from models import Model
from views import View

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from models import Model
    from views import View


class Controller:
    def __init__(self, model: "Model", view: "View") -> None:
        """Initialize controller with model and view

        Args:
            model (Model): _description_
            view (View): _description_
        """
        self.model: Model = model
        self.view: View = view
        self.is_frozen: bool = False
        self.waiting_for_port_selection(dt_ms=100)
        self.update_lines(dt_ms=50)

    def waiting_for_port_selection(self, dt_ms=100) -> None:
        if self.model.is_connected:
            # if COM-port is selected, exit this function
            return
        self.update_available_ports()
        # run program again after a duration (using .after)
        self.view.after(dt_ms, self.waiting_for_port_selection)

    def update_available_ports(self) -> list[str]:
        """Get the list of available COM ports."""
        available_ports = self.model.get_available_ports()
        self.view.after(0, self.view.update_ports(available_ports))

    def open_connection(
        self, port: str, baudrate: int, samples_per_channel: int
    ) -> None:
        """Open a serial connection."""

        try:
            # Open Serial connection in model
            self.model.open_connection(port, baudrate, samples_per_channel)
            self.SAMPLES_PER_CHANNEL: int = int(samples_per_channel)
            # update ui elements
            self.view.update_ui_elements()
        except serial.SerialException as e:
            msg = str(e)
            logger.error(msg)
            self.view.display_error(msg)

    def update_lines(self, dt_ms=100) -> None:
        df: DataFrame = self.model.get_snapshot(is_frozen=self.is_frozen)
        if not df.empty:
            self.view.after(0, lambda: self.view.display_data(data=df))
        self.view.after(dt_ms, lambda: self.update_lines(dt_ms=dt_ms))

    def snapshot_show(self):
        """either freeze or resume visualization"""
        self.is_frozen = not self.is_frozen

        if self.is_frozen:
            logger.info("Freeze image")
            self.model.set_snapshot()
        else:
            logger.info("Unfreeze image")

    def save_snapshot(self):
        if not self.is_frozen:
            self.snapshot_show()
            self.view.after(0, self.save_snapshot)
            return

        df = self.model.get_snapshot(self.is_frozen)

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
