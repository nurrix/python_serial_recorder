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

import logging, serial, threading, time, pandas as pd, numpy as np, tkinter as tk
from typing import Optional
from tkinter import ttk, messagebox, filedialog
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.lines import Line2D
import matplotlib.pyplot as plt
import serial.tools.list_ports as list_ports

logger = logging.getLogger(__name__)
logging.getLogger("PIL").setLevel(logging.WARNING)
logging.getLogger("matplotlib").setLevel(logging.WARNING)

def main() -> None:
    name = "Serial Data Viewer"
    root = tk.Tk(screenName=name, baseName=name, className=name)
    root.geometry(f"{int(root.winfo_screenwidth() // 2)}x{int(root.winfo_screenheight() // (3/2))}")
    model, view = Model(), View(master=root)
    controller = Controller(model, view, update_rate_ms=100)
    view.set_controller(controller=controller)
    root.protocol("WM_DELETE_WINDOW", lambda: on_close(model=model, view=view, root=root))
    root.mainloop()

class Controller:
    def __init__(self, model: "Model", view: "View", update_rate_ms: int = 100) -> None:
        self.model, self.view, self.is_frozen = model, view, False
        self.waiting_for_port_selection(dt_ms=update_rate_ms)
        self.update_graph(dt_ms=update_rate_ms)

    def waiting_for_port_selection(self, dt_ms=100) -> None:
        if self.model.is_connected: return
        self.update_available_ports()
        self.view.after(dt_ms, self.waiting_for_port_selection)

    def update_available_ports(self) -> list[str]:
        available_ports = self.model.get_available_ports()
        self.view.after(0, self.view.update_ports(available_ports))

    def open_connection(self, port: str, baudrate: int, samples_per_channel: int) -> None:
        try:
            self.model.open_connection(port, baudrate, samples_per_channel)
            self.SAMPLES_PER_CHANNEL = samples_per_channel
            self.view.update_ui_elements()
        except serial.SerialException as e:
            self.view.display_error(str(e))

    def update_graph(self, dt_ms=100) -> None:
        def graph_updating_thread():
            while not self.model.is_connected: time.sleep(dt_ms / 1000.0)
            while self.model.is_connected:
                df = self.model.get_snapshot(is_frozen=self.is_frozen)
                if df is not None and not df.empty:
                    self.view.after(0, lambda: self.view.display_data(data=df))
                time.sleep(dt_ms / 1000.0)
        threading.Thread(target=graph_updating_thread, name="update_graph", daemon=True).start()

    def snapshot_show(self):
        self.is_frozen = not self.is_frozen
        if self.is_frozen: self.model.update_snapshot()

    def save_snapshot(self):
        if self.is_running:
            self.snapshot_show()
            self.view.after(0, self.save_snapshot)
            return
        df = self.model.get_snapshot(is_frozen=self.is_frozen)
        if df.empty:
            self.snapshot_show()
            self.view.after(0, lambda: self.view.display_error("Nothing to save, unfreezing."))
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("CSV files", "*.csv"), ("JSON files", "*.json"), ("All files", "*.*")],
            title="Save Timeseries",
        )
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
            self.view.after(0, lambda: self.view.display_error(msg))
            return
        self.view.after(0, lambda: self.view.display_success(msg))

    @property
    def is_running(self):
        return not self.is_frozen

class View(tk.Frame):
    def __init__(self, master: tk.Toplevel) -> None:
        super().__init__(master)
        self.master = master
        self.setup_ui()
        self.pack(fill="both", expand=True)

    def on_key_press(self, event: tk.Event):
        match event.keysym:
            case "space":
                self.controller.snapshot_show()
            case "s" | "S":
                self.controller.snapshot_show()
                self.after(0, self.controller.save_snapshot)

    def set_controller(self, controller: "Controller"):
        self.controller = controller

    def setup_ui(self):
        control_frame = tk.Frame(self)
        control_frame.pack(pady=10)
        selection_frame = tk.Frame(control_frame)
        selection_frame.grid(row=0, column=0, rowspan=4, padx=5, pady=5, sticky="n")
        tk.Label(selection_frame, text="Select COM Port:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.port = ttk.Combobox(selection_frame, state="readonly", width=20)
        self.port.grid(row=0, column=1, padx=5, pady=5)
        tk.Label(selection_frame, text="Select Baudrate:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.baudrate = ttk.Combobox(selection_frame, values=[9600, 115200, 921600], state="readonly", width=20)
        self.baudrate.set(921600)
        self.baudrate.grid(row=1, column=1, padx=5, pady=5)
        tk.Label(selection_frame, text="Select Number of samples (per channel):").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.samples_per_channel = tk.IntVar(self, value=1000)
        self.samples_per_channel_spin = tk.Spinbox(selection_frame, from_=10, to=100_000, increment=100, textvariable=self.samples_per_channel)
        self.samples_per_channel_spin.grid(row=2, column=1, padx=5, pady=5)
        self.connect_button = tk.Button(selection_frame, text="Connect", command=self.on_connect, width=20)
        self.connect_button.grid(row=3, column=0, columnspan=2, pady=10)
        self.keybindings_frame = tk.Frame(control_frame, bg="white")
        self.keybindings_frame.grid(row=0, column=1, padx=10, pady=5, sticky="n")
        self.keybindings_frame.grid_remove()
        tk.Label(self.keybindings_frame, text="Key Bindings:", bg="white").pack(pady=5)
        tk.Label(self.keybindings_frame, text="[Space]: Freeze / Unfreeze", bg="white").pack(pady=2)
        tk.Label(self.keybindings_frame, text="[S]: Save data to file", bg="white").pack(pady=2)
        self.fig, self.ax = plt.subplots()
        self.ax.set_title("Real-time ADC Data")
        self.ax.set_xlabel("Samples")
        self.ax.set_ylabel("ADC Output")
        self.ax.grid(True)
        self.lines = []
        self.canvas = FigureCanvasTkAgg(self.fig, self)
        self.canvas.get_tk_widget().pack(pady=0, fill="both", expand=True)

    def display_data(self, data: pd.DataFrame):
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

    def display_error(self, message: str):
        messagebox.showerror("Error", message)

    def display_success(self, message: str):
        messagebox.showinfo("Success", message)

    def on_connect(self):
        try:
            port, baudrate, samples_per_channel = self.port.get(), int(self.baudrate.get()), self.samples_per_channel.get()
            if not port: raise ValueError("Please select a COM port.")
            if baudrate <= 0: raise ValueError("Please select a valid baudrate.")
            self.controller.open_connection(port=port, baudrate=baudrate, samples_per_channel=samples_per_channel)
            self.keybindings_frame.grid()
        except Exception as e:
            self.display_error(f"Error: {str(e)}")

    def update_ports(self, available_ports):
        if set(available_ports) == set(self.port["values"]): return
        selected_port = self.port.get()
        self.port["values"] = available_ports
        if selected_port in available_ports:
            self.port.set(selected_port)
        elif available_ports:
            self.port.set(available_ports[-1])
        else:
            self.port.set("")

    def update_ui_elements(self):
        self.master.bind("<KeyPress>", self.on_key_press)
        self.port.config(state="disabled")
        self.baudrate.config(state="disabled")
        self.connect_button.config(state="disabled")
        self.samples_per_channel_spin.config(state="disabled")

class Model:
    def __init__(self):
        self.serial_connection, self.read_thread, self.is_reading, self.SAMPLES_PER_CHANNEL = None, None, False, None
        self.__buffer, self.__df_update_lock = pd.DataFrame(), threading.Lock()

    def open_connection(self, port: str, baudrate: int, samples_per_channel: int) -> tuple[bool, Optional[str]]:
        if self.is_connected: raise serial.SerialException("Already connected to a serial port.")
        try:
            self.serial_connection = serial.Serial(port, baudrate)
            self.SAMPLES_PER_CHANNEL = samples_per_channel
            self.read_thread = threading.Thread(target=self.start_continuous_read_from_serial, name="SerialReader", daemon=True)
            self.read_thread.start()
        except serial.SerialException as e:
            raise serial.SerialException(f"Error opening serial port: {str(e)}")

    def start_continuous_read_from_serial(self, updaterate_sec: float = 1 / 50):
        def str_to_intarray(data: str):
            return list(map(int, data.split(" ")))

        def calculate_2D_matrix(data) -> tuple[int, int]:
            num_rows = len(data)
            num_cols = len(data[0]) if num_rows else 0
            return num_rows, num_cols

        def str_contains_only_numbers(row: str):
            return row and all(c.isdigit() or c == " " for c in row)

        self.read(flag=True)
        rest, counter = "", 0
        while self.is_connected:
            try:
                available_bytes = self.serial_connection.in_waiting
            except Exception:
                available_bytes = 0
            if available_bytes < 100:
                time.sleep(updaterate_sec)
                continue
            bytes = self.serial_connection.read(available_bytes)
            try:
                ascii_data = rest + bytes.decode()
            except UnicodeDecodeError:
                logger.warning("read unknown non-character bytes.")
                rest = ""
                continue
            row_asci_data = ascii_data.split("\r\n")
            rest = row_asci_data[-1]
            if len(row_asci_data) < 2: continue
            data = row_asci_data[:-2]
            data_filtered = filter(str_contains_only_numbers, data)
            data_integers = list(map(str_to_intarray, data_filtered))
            num_rows, num_channels = calculate_2D_matrix(data_integers)
            if num_rows == 0 or num_channels == 0: continue
            column_names = [f"Ch{i}" for i in range(num_channels)]
            dfnew = pd.DataFrame(data_integers, index=range(counter, counter + num_rows), columns=column_names)
            self.update_df(data=dfnew)
            counter += num_rows
            time.sleep(updaterate_sec)

    def update_df(self, data: pd.DataFrame) -> None:
        with self.__df_update_lock:
            if self.__buffer.shape[1] != data.shape[1]:
                sz = (self.SAMPLES_PER_CHANNEL, data.shape[1])
                self.__buffer = pd.DataFrame(np.zeros(sz), columns=data.columns, index=range(-self.SAMPLES_PER_CHANNEL, 0), dtype=int)
            self.__buffer = pd.concat([self.__buffer, data], ignore_index=False)
            if len(self.__buffer) > self.SAMPLES_PER_CHANNEL:
                self.__buffer = self.__buffer.iloc[-self.SAMPLES_PER_CHANNEL:]

    def close_connection(self) -> None:
        if self.is_connected:
            self.read(False)
            self.serial_connection.close()

    def get_available_ports(self) -> list[str]:
        ports = [port.device for port in list_ports.comports()]
        return sorted(list(set(ports))) if ports else []

    def read(self, flag: bool) -> None:
        self.is_reading = flag and self.is_connected
        if self.is_disconnected: return
        msg = b"s" if flag else b"e"
        try:
            self.serial_connection.write(msg)
        except serial.SerialException as e:
            logger.error(str(e))

    def update_snapshot(self) -> None:
        with self.__df_update_lock:
            self.__snapshot = self.__buffer.copy()

    def get_snapshot(self, is_frozen: bool) -> pd.DataFrame | None:
        if not self.is_reading: return None
        with self.__df_update_lock:
            return self.__snapshot.copy() if is_frozen else self.__buffer.copy()

    @property
    def is_connected(self) -> bool:
        return self.serial_connection and self.serial_connection.is_open and self.read_thread.is_alive

    @property
    def is_disconnected(self) -> bool:
        return not self.is_connected

    def __del__(self) -> None:
        self.close_connection()

def on_close(model: Model, view: View, root: tk.Toplevel) -> None:
    model.close_connection()
    view.destroy()
    root.quit()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logger.info("Starting Serial Recorder...")
    main()
    logger.info("Exiting...")
