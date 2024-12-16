import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.lines import Line2D
import matplotlib.pyplot as plt


import logging

import pandas as pd

logger = logging.getLogger(__name__)
logging.getLogger('PIL').setLevel(logging.WARNING)  # Suppress debug/info messages from requests
logging.getLogger('matplotlib').setLevel(logging.WARNING)  # Suppress debug/info messages from requests

if TYPE_CHECKING:
    from controller import SerialController  # Only imported for type hinting
class SerialApp(tk.Frame):
    def __init__(self, master:tk.Toplevel=None):
        super().__init__(master, width=800, height=600)
        self.master = master
        self.setup_ui()
        
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.pack()
        
    def set_controller(self, controller: "SerialController"):
        self.controller = controller

    def setup_ui(self):

        # COM Port Dropdown
        self.port_label = tk.Label(self, text="Select COM Port:")
        self.port_label.pack(pady=5)

        self.port_combobox = ttk.Combobox(self, state="readonly", width=20)
        self.port_combobox.pack(pady=5)

        # Baudrate Dropdown
        self.baudrate_label = tk.Label(self, text="Select Baudrate:")
        self.baudrate_label.pack(pady=5)

        self.baudrate_combobox = ttk.Combobox(self, values=[9600, 115200], state="readonly", width=20)
        self.baudrate_combobox.set(115200)
        self.baudrate_combobox.pack(pady=5)

        # Sampling Rate Dropdown
        self.sampling_rate_label = tk.Label(self, text="Select Sampling Rate (ms):")
        self.sampling_rate_label.pack(pady=5)

        self.sampling_rate_combobox = ttk.Combobox(self, values=[1000, 500, 2000], state="readonly", width=20)
        self.sampling_rate_combobox.set(1000)
        self.sampling_rate_combobox.pack(pady=5)

        # Connect Button
        self.connect_button = tk.Button(self, text="Connect", command=self.on_connect)
        self.connect_button.pack(pady=10)

        # Matplotlib Plot Area (Embedded)
        self.fig, self.ax = plt.subplots(figsize=(6, 4))
        self.ax.set_title("Real-time ADC Data")
        self.ax.set_xlabel("Samples")
        self.ax.set_ylabel("ADC Output")
        self.ax.legend()
        self.line: list[Line2D] = None

        self.canvas = FigureCanvasTkAgg(self.fig, self)
        self.canvas.get_tk_widget().pack(pady=10)

        self.data = []  # Store the data for plotting

    def display_data(self, data: pd.DataFrame):
        """Update the graph with new data."""
        if self.line is None:
            self.line = []
            for idx, name in enumerate(data.columns):
                l = Line2D(data.index, data[name], label=name,)
                self.line.append(l)
                self.ax.add_line(l)
        else:
            # Update the plot
            for idx, name in enumerate(data.columns):
                self.line[idx].set_ydata(data[name])
                self.line[idx].set_xdata(data.index.to_list())
                
        self.ax.relim()  # Recalculate limits
        self.ax.autoscale_view()
        self.canvas.draw()  # Redraw the canvas

    def display_error(self, message: str):
        """Display error messages."""
        tk.messagebox.showerror("Error", message)

    def on_connect(self):
        """Connect to the selected COM port and baudrate."""
        try:
            port = self.port_combobox.get()
            baudrate = int(self.baudrate_combobox.get())
            sampling_rate = int(self.sampling_rate_combobox.get())
            duration = 5
            if not port:
                raise ValueError("Please select a COM port.")
            if baudrate <= 0:
                raise ValueError("Please select a valid baudrate.")

            self.controller.open_connection(port, baudrate, sampling_rate, duration)

        except ValueError as e:
            logger.error(str(e))
            self.display_error(f"Error: {e}")
        except Exception as e:
            logger.error(str(e))
            self.display_error(f"Error: {str(e)}")


    def update_ports(self, available_ports):
        """Update the available ports dropdown. Preserve the selected port if still available."""
        # If the previously selected port is still available, keep it selected.
        if set(available_ports) == set(self.port_combobox['values']):
            return
        selected_port = self.port_combobox.get()
        self.port_combobox['values'] = available_ports
        if selected_port in available_ports:
            self.port_combobox.set(selected_port)  # Keep the previously selected port.
        elif available_ports:
            self.port_combobox.set(available_ports[0])  # Set to first available port
        else:
            self.port_combobox.set('')  # Clear if no ports available
        

    def on_close(self):
        self.controller.close_connection()
        self.destroy()
        self.master.quit()  # Close the Tkinter window