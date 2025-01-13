#!/usr/bin/env python3

"""
Serial Data Viewer

This program is a graphical user interface (GUI) application that allows users to view and record data from a serial port in real-time. It follows the Model-View-Controller (MVC) design pattern to separate concerns and improve maintainability.

- Model: Handles the data and serial communication.
- View: Manages the graphical user interface using Tkinter and Matplotlib.
- Controller: Coordinates between the Model and View, handling user interactions and updating the view with new data.

Features:
- Automatically detects available COM ports.
- Allows users to select a COM port, baud rate, and number of samples per channel.
- Displays real-time data from the serial port in a graph.
- Allows users to freeze/unfreeze the data display.
- Provides options to save the data as CSV, Excel, or JSON files.

"""

import logging
import serial
import serial.tools.list_ports as list_ports
import threading
import time
from typing import Optional
import pandas as pd
import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.lines import Line2D
import matplotlib.pyplot as plt
import openpyxl

logger = logging.getLogger(__name__)
logging.getLogger("PIL").setLevel(
    logging.WARNING
)  # Suppress debug/info messages from Pillow
logging.getLogger("matplotlib").setLevel(
    logging.WARNING
)  # Suppress debug/info messages from matplotlib


def main() -> None:
    # Create the Tkinter root window
    name = "Serial Data Viewer"
    root: tk.Toplevel = tk.Tk(screenName=name, baseName=name, className=name)
    root.geometry(
        f"{int(root.winfo_screenwidth() // 2)}x{int(root.winfo_screenheight() // (3/2))}"
    )

    # Create UI using the MVC pattern (Model, View, Controller)
    model = Model()
    view = View(master=root)
    controller = Controller(model, view, update_rate_ms=100)
    view.set_controller(controller=controller)

    # Set a close script, using the WM_DELETE_WINDOW protocol
    root.protocol(
        "WM_DELETE_WINDOW",
        lambda: on_close(model=model, view=view, root=root),  # noqa: F821
    )

    # Start the Tkinter event loop
    root.mainloop()


class Controller:
    """Controller of the program"""

    def __init__(self, model: "Model", view: "View", update_rate_ms: int = 100) -> None:
        """Initialize controller with model and view"""
        self.model: Model = model
        self.view: View = view
        self.is_frozen: bool = False
        self.waiting_for_port_selection(dt_ms=update_rate_ms)
        self.update_graph(dt_ms=update_rate_ms)

    def waiting_for_port_selection(self, dt_ms=100) -> None:
        """update available ports efter ~10ms until connection is made."""
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
            self.SAMPLES_PER_CHANNEL: int = samples_per_channel
            # update ui elements
            self.view.update_ui_elements()
        except serial.SerialException as e:
            self.view.display_error(str(e))

    def update_graph(self, dt_ms=100) -> None:
        """Create a thread to periodically update data if new data is available."""

        def graph_updating_thread():
            # wait for model to connect
            while not self.model.is_connected:
                time.sleep(dt_ms / 1000.0)

            while self.model.is_connected:
                df: pd.DataFrame = self.model.get_snapshot(is_frozen=self.is_frozen)
                if df is not None and not df.empty:
                    self.view.after(0, lambda: self.view.display_data(data=df))
                time.sleep(dt_ms / 1000.0)

        threading.Thread(target=graph_updating_thread, name="update_graph", daemon=True).start()

    def snapshot_show(self):
        """either freeze or resume visualization"""
        self.is_frozen = not self.is_frozen

        if self.is_frozen:
            self.model.update_snapshot()

    def save_snapshot(self):
        if self.is_running:
            self.snapshot_show()
            self.view.after(0, self.save_snapshot)
            return

        df = self.model.get_snapshot(is_frozen=self.is_frozen)

        if df.empty:
            # If dataframe is empty, restart recording, and cancel save
            self.snapshot_show()
            self.view.after(
                0, lambda: self.view.display_error("Nothing to save, unfreezing.")
            )
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
            msg = f"Data saved as CSV to {file_path}"

        # Save as Excel
        elif file_path.endswith(".xlsx"):
            df.to_excel(file_path, index=True)
            msg = f"Data saved as Excel to {file_path}"

        # Save as JSON
        elif file_path.endswith(".json"):
            df.to_json(file_path, orient="records", lines=True)
            msg = f"Data saved as JSON to {file_path}"

        else:
            msg = "Invalid file format. Please save as CSV, Excel, or JSON."
            self.view.after(0, lambda: self.view.display_error(msg))
            return

        self.view.after(0, lambda: self.view.display_success(msg))

    @property
    def is_running(self):
        return not self.is_frozen


class View(tk.Frame):
    """UI view of data"""

    def __init__(self, master: tk.Toplevel) -> None:
        super().__init__(master)
        self.master = master
        self.setup_ui()
        self.pack(fill="both", expand=True)

    def on_key_press(self, event: tk.Event):
        """key press handler"""
        match event.keysym:
            case "space":
                # freeze/unfreeze the data, and create a fixed snapshot
                self.controller.snapshot_show()
            case "s" | "S":
                # Save the snapshot to a file
                self.controller.snapshot_show()
                self.after(0, self.controller.save_snapshot)

    def set_controller(self, controller: "Controller"):
        self.controller = controller

    def setup_ui(self):
        """Setup of UI elements"""
        # Create a frame for the controls and their descriptions
        control_frame = tk.Frame(self)
        control_frame.pack(pady=10)

        # Create a frame for the selection controls
        selection_frame = tk.Frame(control_frame)
        selection_frame.grid(row=0, column=0, rowspan=4, padx=5, pady=5, sticky="n")

        # COM Port Dropdown
        tk.Label(selection_frame, text="Select COM Port:").grid(
            row=0, column=0, padx=5, pady=5, sticky="w"
        )
        self.port = ttk.Combobox(selection_frame, state="readonly", width=20)
        self.port.grid(row=0, column=1, padx=5, pady=5)

        # Baudrate Dropdown
        tk.Label(selection_frame, text="Select Baudrate:").grid(
            row=1, column=0, padx=5, pady=5, sticky="w"
        )
        self.baudrate = ttk.Combobox(
            selection_frame, values=[9600, 115200, 921600], state="readonly", width=20
        )
        self.baudrate.set(921600)
        self.baudrate.grid(row=1, column=1, padx=5, pady=5)

        # Number of Samples Dropdown
        tk.Label(selection_frame, text="Select Number of samples (per channel):").grid(
            row=2, column=0, padx=5, pady=5, sticky="w"
        )
        self.samples_per_channel = tk.IntVar(
            self, value=1000
        )  # Set default value to 1000
        self.samples_per_channel_spin = tk.Spinbox(
            selection_frame,
            from_=10,
            to=100_000,
            increment=100,
            textvariable=self.samples_per_channel,
        )
        self.samples_per_channel_spin.grid(row=2, column=1, padx=5, pady=5)

        # Connect Button
        self.connect_button = tk.Button(
            selection_frame, text="Connect", command=self.on_connect, width=20
        )
        self.connect_button.grid(row=3, column=0, columnspan=2, pady=10)

        # Create a frame for the key bindings
        self.keybindings_frame = tk.Frame(control_frame, bg="white")
        self.keybindings_frame.grid(row=0, column=1, padx=10, pady=5, sticky="n")
        self.keybindings_frame.grid_remove()  # Hide initially

        # Key Bindings Explanation
        tk.Label(self.keybindings_frame, text="Key Bindings:", bg="white").pack(pady=5)
        tk.Label(
            self.keybindings_frame, text="[Space]: Freeze / Unfreeze", bg="white"
        ).pack(pady=2)
        tk.Label(
            self.keybindings_frame, text="[S]: Save data to file", bg="white"
        ).pack(pady=2)

        # Matplotlib Plot Area (Embedded)
        self.fig, self.ax = plt.subplots()
        self.ax.set_title("Real-time ADC Data")
        self.ax.set_xlabel("Samples")
        self.ax.set_ylabel("ADC Output")
        self.ax.grid(True)
        self.lines: list[Line2D] = []

        self.canvas = FigureCanvasTkAgg(self.fig, self)
        self.canvas.get_tk_widget().pack(
            pady=0,
            fill="both",
            expand=True,
        )

    def display_data(self, data: pd.DataFrame):
        """Update the graph with new data."""

        COLORS = plt.rcParams["axes.prop_cycle"].by_key()["color"]
        if len(self.lines) != len(data.columns):
            for line in self.lines:
                line.remove()
            self.lines.clear()
            # Initiate lines in figure
            for idx, name in enumerate(data.columns):
                line = Line2D(
                    xdata=data.index,
                    ydata=data[name],
                    label=name,
                    color=COLORS[idx % len(COLORS)],
                )
                self.lines.append(line)
                self.ax.add_line(line)
            self.ax.legend(loc="upper left")
        else:
            # Update the plot
            for name, line in zip(data.columns, self.lines):
                line.set_data(data.index.to_list(), data[name])

        self.ax.relim()  # Recalculate limits
        self.ax.autoscale_view()
        self.canvas.draw()  # Redraw the canvas

    def display_error(self, message: str):
        """Display error messages."""
        messagebox.showerror("Error", message)

    def display_success(self, message: str):
        """Display error messages."""
        messagebox.showinfo("Error", message)

    def on_connect(self):
        """Connect to the selected COM port and baudrate."""
        try:
            port: str = self.port.get()
            baudrate = int(self.baudrate.get())
            samples_per_channel = self.samples_per_channel.get()
            if not port:
                raise ValueError("Please select a COM port.")
            if baudrate <= 0:
                raise ValueError("Please select a valid baudrate.")

            self.controller.open_connection(
                port=port, baudrate=baudrate, samples_per_channel=samples_per_channel
            )
            self.keybindings_frame.grid()  # Show key bindings after connecting

        except Exception as e:
            self.display_error(f"Error: {str(e)}")

    def update_ports(self, available_ports):
        """Update the available ports dropdown. Preserve the selected port if still available."""
        # If the previously selected port is still available, keep it selected.
        if set(available_ports) == set(self.port["values"]):
            return
        selected_port = self.port.get()
        self.port["values"] = available_ports
        if selected_port in available_ports:
            self.port.set(selected_port)  # Keep the previously selected port.
        elif available_ports:
            self.port.set(available_ports[-1])  # Set to first available port
        else:
            self.port.set("")  # Clear if no ports available

    def update_ui_elements(self):
        """disable buttons and dropdows, and activate keybindings"""
        # activate keybindings
        self.master.bind("<KeyPress>", self.on_key_press)

        # disable buttons
        self.port.config(state="disabled")
        self.baudrate.config(state="disabled")
        self.connect_button.config(state="disabled")
        self.samples_per_channel_spin.config(state="disabled")


class Model:
    """Model class for the MVC pattern."""

    def __init__(self):
        """Initialize the model."""
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

        def str_to_intarray(data: str):
            """Convert a string of numbers separated by spaces to a list of integers."""
            return list(map(int, data.split(" ")))

        def calculate_2D_matrix(data) -> tuple[int, int]:
            """Calculate the number of rows and columns in a 2D matrix."""
            num_rows: int = len(data)
            if num_rows == 0:
                num_cols = 0
            else:
                num_cols = len(data[0])
            return num_rows, num_cols

        def str_contains_only_numbers(row: str):
            """Check if a string contains only numbers and spaces."""
            return row and all(c.isdigit() or c == " " for c in row)

        # write to esp32, that it needs to write data
        self.read(flag=True)
        rest: str = ""
        counter: int = 0
        while self.is_connected:
            try:
                available_bytes: int = self.serial_connection.in_waiting
            except Exception:
                available_bytes = 0

            if available_bytes < 100:
                time.sleep(updaterate_sec)
                continue

            # read n available bytes from serial connection (bytes)
            bytes: bytearray = self.serial_connection.read(available_bytes)
            try:
                ascii_data: str = rest + bytes.decode()
            except UnicodeDecodeError as _:
                # if error
                logger.warning("read unknown non-character bytes.")
                rest = ""
                continue

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
                    np.zeros(sz),
                    columns=data.columns,
                    index=range(-self.SAMPLES_PER_CHANNEL, 0),
                    dtype=int,
                )
            # Append new data to buffer
            self.__buffer: pd.DataFrame = pd.concat(
                [self.__buffer, data], ignore_index=False
            )

            # If the buffer is larger than the specified number of samples, remove the oldest samples
            if len(self.__buffer) > self.SAMPLES_PER_CHANNEL:
                self.__buffer: pd.DataFrame = self.__buffer.iloc[
                    -self.SAMPLES_PER_CHANNEL :
                ]

    def close_connection(self) -> None:
        """Close the serial connection."""
        if self.is_connected:
            self.read(False)
            self.serial_connection.close()

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
        return (
            self.serial_connection
            and self.serial_connection.is_open
            and self.read_thread.is_alive
        )

    @property
    def is_disconnected(self) -> bool:
        """ Return True if serial is connected to COM port is not connected """
        return not self.is_connected

    def __del__(self) -> None:
        """destructor"""
        self.close_connection()


def on_close(model: Model, view: View, root: tk.Toplevel) -> None:
    """ When closing window, system needs to be shut down correctly! """
    model.close_connection()  # close serial connection
    view.destroy()
    root.quit()


if __name__ == "__main__":
    # Set up basic configuration for logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger.info("Starting Serial Recorder...")
    main()
    logger.info("Exititing...")
