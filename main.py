#!/usr/bin/env python3

"""
Serial Data Viewer

This program is a graphical user interface (GUI) application that allows users to view and record data from a serial port in real-time.
It follows the Model-View-Controller (MVC) design pattern to separate concerns and improve maintainability.

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
import threading
import time
import pandas as pd
import numpy as np
import tkinter as tk
from typing import Optional
from tkinter import ttk, filedialog
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.lines import Line2D
import matplotlib.pyplot as plt
import serial.tools.list_ports as list_ports
from tkinter.scrolledtext import ScrolledText


def main() -> None:
    """Main function to set up the GUI and start the application."""
    name = "Serial Data Viewer"
    root = tk.Tk(screenName=name, baseName=name, className=name)
    root.geometry(f"{int(root.winfo_screenwidth() // 2)}x{int(root.winfo_screenheight() // (3 / 2))}")
    model, view = Model(), View(master=root)
    controller = Controller(model, view, update_rate_ms=100)
    view.set_controller(controller=controller)
    root.protocol("WM_DELETE_WINDOW", lambda: on_close(model=model, view=view, root=root))
    root.mainloop()


class Controller:
    """Controller class to manage interactions between the Model and View."""

    def __init__(self, model: "Model", view: "View", update_rate_ms: int = 100) -> None:
        self.model, self.view, self.is_frozen = model, view, False
        self.waiting_for_port_selection(dt_ms=update_rate_ms)
        self.update_graph(dt_ms=update_rate_ms)

    def waiting_for_port_selection(self, dt_ms=100) -> None:
        """Update available ports until a connection is made."""
        if self.model.is_connected:
            return
        self.update_available_ports()
        self.view.after(dt_ms, self.waiting_for_port_selection)

    def update_available_ports(self) -> list[str]:
        """Get the list of available COM ports and update the view."""
        available_ports = self.model.get_available_ports()
        self.view.after(0, lambda available_ports=available_ports: self.view.update_ports(available_ports))

    def open_connection(self, port: str, baudrate: int, samples_per_channel: int) -> None:
        """Open a serial connection and update the UI elements."""
        self.model.open_connection(port, baudrate, samples_per_channel)
        self.SAMPLES_PER_CHANNEL = samples_per_channel
        self.view.update_ui_elements()

    def update_graph(self, dt_ms=100) -> None:
        """Create a thread to periodically update data if new data is available."""

        def graph_updating_thread():
            while not self.model.is_connected:
                time.sleep(dt_ms / 1000.0)

            while self.model.is_connected:
                t1 = time.time()
                try:
                    if self.view.winfo_ismapped():
                        df = self.model.get_snapshot(is_frozen=self.is_frozen)
                        if df is not None and not df.empty:
                            self.view.after(0, lambda: self.view.display_data(data=df))
                except Exception as e:
                    logging.error(f"Stopped graph updater due to error.\n{e}")
                    return
                dt = time.time() - t1
                time.sleep(max(dt_ms / 1000.0 - dt, 0))

        threading.Thread(target=graph_updating_thread, name="update_graph", daemon=True).start()

    def snapshot_show(self):
        """Toggle freezing and unfreezing of the data display."""
        self.is_frozen = not self.is_frozen

        if self.is_frozen:
            self.model.update_snapshot()

    def save_snapshot(self):
        """Save the current snapshot to a file."""
        if self.is_running:
            self.snapshot_show()
            self.view.after(0, self.save_snapshot)
            return

        df = self.model.get_snapshot(is_frozen=self.is_frozen)
        if df.empty:
            self.snapshot_show()
            logging.error("Nothing to save, unfreezing.")
            logging.warning("Attempted to save an empty snapshot.")
            return
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
        if file_path == "":
            pass
        if file_path.endswith(".csv"):
            df.to_csv(file_path, index=True)
            msg = f"Data saved as CSV to {file_path}"
        elif file_path.endswith(".xlsx"):
            df.to_excel(file_path, index=True)
            msg = f"Data saved as Excel to {file_path}"
        elif file_path.endswith(".json"):
            df.to_json(file_path, orient="records", lines=True)
            msg = f"Data saved as JSON to {file_path}"
        else:
            msg = "Invalid file format. Please save as CSV, Excel, or JSON."
            logging.error(msg)
            return
        logging.info(msg)

    @property
    def is_running(self):
        """Check if the data display is running."""
        return not self.is_frozen


class View(tk.Frame):
    """View class to manage the graphical user interface."""

    def __init__(self, master: tk.Toplevel) -> None:
        super().__init__(master)
        self.master = master
        self.setup_ui()
        self.pack(fill="both", expand=True)

    def on_key_press(self, event: tk.Event):
        """Handle key press events."""
        match event.keysym:
            case "space":  # pause / resume
                self.controller.snapshot_show()
            case "s" | "S":  # Save current snapshot (or freeze then save)
                self.after(0, self.controller.save_snapshot)

    def set_controller(self, controller: "Controller"):
        """Set the controller for the view."""
        self.controller = controller

    def setup_ui(self):
        """Set up the UI elements."""

        control_frame = tk.Frame(self)
        control_frame.pack(pady=10)

        selection_frame = tk.Frame(control_frame)
        selection_frame.grid(row=0, column=0, rowspan=4, padx=5, pady=5, sticky="n")

        lbl = tk.Label(selection_frame, text="Select COM Port:")
        lbl.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.port = ttk.Combobox(selection_frame, state="readonly", width=20)
        self.port.grid(row=0, column=1, padx=5, pady=5)

        lbl = tk.Label(selection_frame, text="Select Baudrate:")
        lbl.grid(row=1, column=0, padx=5, pady=5, sticky="w")

        BAUDRATE_OPTIONS = [9600, 115200, 256000, 512000, 921600]
        self.baudrate = ttk.Combobox(selection_frame, values=BAUDRATE_OPTIONS, state="readonly", width=20)
        self.baudrate.set(921600)
        self.baudrate.grid(row=1, column=1, padx=5, pady=5)

        lbl = tk.Label(selection_frame, text="Select Number of samples (per channel):")
        lbl.grid(row=2, column=0, padx=5, pady=5, sticky="w")

        self.samples_per_channel = tk.IntVar(self, value=1000)
        self.samples_per_channel_spin = tk.Spinbox(
            selection_frame, from_=10, to=100_000, increment=100, textvariable=self.samples_per_channel
        )
        self.samples_per_channel_spin.grid(row=2, column=1, padx=5, pady=5)
        self.connect_button = tk.Button(selection_frame, text="Connect", command=self.on_connect, width=20)
        self.connect_button.grid(row=3, column=0, columnspan=2, pady=10)
        self.keybindings_frame = tk.Frame(control_frame)
        self.keybindings_frame.grid(row=0, column=1, padx=10, pady=5, sticky="n")
        # self.keybindings_frame.grid_remove()
        tk.Label(self.keybindings_frame, text="Key Bindings:").pack(pady=5)
        tk.Label(self.keybindings_frame, text="[Space]: Freeze / Unfreeze").pack(pady=2)
        tk.Label(self.keybindings_frame, text="[S]: Save data to file").pack(pady=2)
        self.fig, self.ax = plt.subplots()
        self.ax.set_title("Real-time ADC Data")
        self.ax.set_xlabel("Samples")
        self.ax.set_ylabel("ADC Output")
        self.ax.grid(True)
        self.lines: list[Line2D] = []
        self.canvas = FigureCanvasTkAgg(self.fig, self)
        self.canvas.get_tk_widget().pack(pady=0, fill="both", expand=True)

        # logging area
        self.log_area = ScrolledText(self, height=15, width=70, state="disabled")
        self.log_area.pack(pady=10, fill=tk.BOTH)
        self.setup_logger()

    def display_data(self, data: pd.DataFrame):
        """Update the graph with new data."""

        COLORS = plt.rcParams["axes.prop_cycle"].by_key()["color"]
        if len(self.lines) != len(data.columns):
            for line in self.lines:
                line.remove()
            self.lines.clear()
            for idx, name in enumerate(data.columns):
                line = Line2D(xdata=data.index, ydata=data[name], label=name, color=COLORS[idx % len(COLORS)])
                self.lines.append(line)
                self.ax.add_line(line)
            self.ax.legend(loc="upper left")
        else:
            for name, line in zip(data.columns, self.lines):
                line.set_data(data.index.to_list(), data[name])
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw()

    def on_connect(self):
        """Connect to the selected COM port and baudrate."""
        try:
            port, baudrate, samples_per_channel = (
                self.port.get(),
                int(self.baudrate.get()),
                self.samples_per_channel.get(),
            )
            if not port:
                raise ValueError("Please select a COM port.")
            if baudrate <= 0:
                raise ValueError("Please select a valid baudrate.")
            self.controller.open_connection(port=port, baudrate=baudrate, samples_per_channel=samples_per_channel)
            # self.keybindings_frame.grid()
            logging.info(
                f"Connected to port {port} with baudrate {baudrate} and {samples_per_channel} samples per channel."
            )
        except Exception as e:
            logging.error(str(e))

    def update_ports(self, available_ports):
        """Update the available ports dropdown."""
        if set(available_ports) == set(self.port["values"]):
            return
        selected_port = self.port.get()
        self.port["values"] = available_ports
        if selected_port in available_ports:
            self.port.set(selected_port)
        elif available_ports:
            self.port.set(available_ports[-1])
        else:
            self.port.set("")

    def update_ui_elements(self):
        """Disable buttons and dropdowns, and activate keybindings."""
        self.master.bind("<KeyPress>", self.on_key_press)
        self.port.config(state="disabled")
        self.baudrate.config(state="disabled")
        self.connect_button.config(state="disabled")
        self.samples_per_channel_spin.config(state="disabled")

    def setup_logger(self):
        """Set up the logging system to write to the Tkinter Text widget."""
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

        # Create a custom logging handler
        class TextHandler(logging.Handler):
            def __init__(self, widget: tk.Widget):
                super().__init__()
                self.widget = widget

            def emit(self, record):
                if not self.widget.winfo_exists():
                    return
                log_entry = self.format(record) + "\n"
                self.widget.config(state="normal")
                self.widget.insert(tk.END, log_entry)
                self.widget.config(state="disabled")
                self.widget.yview(tk.END)  # Auto-scroll

        self.text_handler = text_handler = TextHandler(self.log_area)
        text_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

        logging.getLogger().addHandler(self.text_handler)


class Model:
    """Model class to handle data and serial communication."""

    def __init__(self):
        self.serial_connection, self.read_thread, self.SAMPLES_PER_CHANNEL = None, None, None
        self.__buffer, self.__df_update_lock = pd.DataFrame(), threading.Lock()

    def open_connection(self, port: str, baudrate: int, samples_per_channel: int) -> tuple[bool, Optional[str]]:
        """Open a serial connection and start reading in a separate thread."""
        if self.is_connected:
            raise serial.SerialException("Already connected to a serial port.")
        try:
            self.serial_connection = serial.Serial(port, baudrate)
            self.SAMPLES_PER_CHANNEL = samples_per_channel
            self.read_thread = threading.Thread(
                target=self.start_continuous_read_from_serial, name="SerialReader", daemon=True
            )
            self.read_thread.start()
        except serial.SerialException as _:
            raise serial.SerialException("Could not open serial connection")

    def start_continuous_read_from_serial(self, updaterate_sec: float = 1.0 / 50.0, failure_duration: float = 3.0):
        """Continuously read data from the serial port in a background thread."""
        rest, counter = "", 0
        if self.is_connected:
            self.serial_connection.flush()
            self.serial_connection.read()

        t0 = time.time()
        ok = True
        while self.is_connected:
            try:
                available_bytes = self.get_available_bytes()

            except serial.SerialException as _:
                self.close_connection()
                logging.error("ESP32 disconnected! Restart the program, if you wish to continue!")
                return

            if not available_bytes:
                if ok:
                    t0 = time.time()

                if time.time() - t0 > failure_duration:
                    self.close_connection()
                    return

                ok = False
                time.sleep(updaterate_sec)
                continue
            ok = True
            ascii_data = self.read_serial_data(available_bytes, rest)
            if ascii_data is None:
                rest = ""
            else:
                rest, data_integers = process_serial_data(ascii_data)
                if data_integers:
                    self.update_dataframe(data_integers, counter)
                    counter += len(data_integers)
            time.sleep(updaterate_sec)

    def get_available_bytes(self) -> int:
        """Get the number of available bytes in the serial connection."""
        return self.serial_connection.in_waiting

    def read_serial_data(self, available_bytes: int, rest: str) -> Optional[str]:
        """Read data from the serial connection and decode it."""
        try:
            bytes = self.serial_connection.read(available_bytes)
            return rest + bytes.decode()
        except UnicodeDecodeError:
            logging.warning("Read unknown non-character bytes.")
            return None

    def update_dataframe(self, data_integers: list[list[int]], counter: int) -> None:
        """Update the DataFrame with new data."""
        num_rows, num_channels = calculate_2D_matrix(data_integers)
        if num_rows == 0 or num_channels == 0:
            return
        column_names = [f"Ch{i}" for i in range(num_channels)]
        dfnew = pd.DataFrame(data_integers, index=range(counter, counter + num_rows), columns=column_names)
        self.update_df(data=dfnew)

    def update_df(self, data: pd.DataFrame) -> None:
        """Update the buffer with new data."""
        with self.__df_update_lock:
            if self.__buffer.shape[1] != data.shape[1]:
                sz = (self.SAMPLES_PER_CHANNEL, data.shape[1])
                self.__buffer = pd.DataFrame(
                    np.zeros(sz), columns=data.columns, index=range(-self.SAMPLES_PER_CHANNEL, 0), dtype=int
                )
            self.__buffer = pd.concat([self.__buffer, data], ignore_index=False)
            if len(self.__buffer) > self.SAMPLES_PER_CHANNEL:
                self.__buffer = self.__buffer.iloc[-self.SAMPLES_PER_CHANNEL :]

    def close_connection(self) -> None:
        """Close the serial connection."""
        if self.is_connected:
            self.serial_connection.close()

    def get_available_ports(self) -> list[str]:
        """Get the list of available COM ports."""
        return sorted([port.device for port in list_ports.comports()])

    def update_snapshot(self) -> None:
        """Copy the current buffer into a snapshot."""
        with self.__df_update_lock:
            self.__snapshot = self.__buffer.copy()

    def get_snapshot(self, is_frozen: bool) -> pd.DataFrame | None:
        """Return a snapshot of the data or the buffer."""
        if not self.is_connected:
            return self.__snapshot.copy()
        with self.__df_update_lock:
            return self.__snapshot.copy() if is_frozen else self.__buffer.copy()

    @property
    def is_connected(self) -> bool:
        """Check if the serial connection is established."""
        b = self.serial_connection and self.serial_connection.is_open and self.read_thread.is_alive()
        return b

    @property
    def is_disconnected(self) -> bool:
        """Check if the serial connection is not established."""
        return not self.is_connected

    def __del__(self) -> None:
        """Destructor to close the serial connection."""
        self.close_connection()


def process_serial_data(ascii_data: str) -> tuple[str, list[list[int]]]:
    """Process the ASCII data read from the serial connection."""
    row_asci_data = ascii_data.split("\r\n")
    rest = row_asci_data[-1]
    if len(row_asci_data) < 2:
        return rest, []
    data = row_asci_data[:-2]
    data_filtered = filter(str_contains_only_numbers, data)
    data_integers = list(map(str_to_intarray, data_filtered))
    return rest, data_integers


def str_contains_only_numbers(row: str) -> bool:
    """Check if a string contains only numbers and spaces."""
    return row and all(c.isdigit() or c == " " for c in row)


def str_to_intarray(data: str) -> list[int]:
    """Convert a string of numbers separated by spaces to a list of integers."""
    return list(map(int, data.split(" ")))


def calculate_2D_matrix(data: list[list[int]]) -> tuple[int, int]:
    """Calculate the number of rows and columns in a 2D matrix."""
    num_rows = len(data)
    num_cols = len(data[0]) if num_rows else 0
    return num_rows, num_cols


def on_close(model: Model, view: View, root: tk.Toplevel) -> None:
    """Close the application and clean up resources."""
    model.close_connection()
    view.destroy()
    root.quit()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
        filename="log.log",
        filemode="w",
    )
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s")
    )
    logging.getLogger().addHandler(console_handler)
    logging.getLogger("PIL").setLevel(logging.WARNING)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)

    logging.info("Starting Serial Recorder...")
    main()
    logging.info("Exiting...")
