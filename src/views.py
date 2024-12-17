import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.lines import Line2D
import matplotlib.pyplot as plt

import logging
import pandas as pd

logger = logging.getLogger(__name__)

logging.getLogger("PIL").setLevel(
    logging.WARNING
)  # Suppress debug/info messages from Pillow
logging.getLogger("matplotlib").setLevel(
    logging.WARNING
)  # Suppress debug/info messages from matplotlib

if TYPE_CHECKING:
    from controller import Controller  # Only imported for type hinting


class View(tk.Frame):
    def __init__(self, master: tk.Toplevel) -> None:
        super().__init__(master)
        self.master = master
        self.setup_ui()

        self.pack(fill="both", expand=True)

    def on_key_press(self, event: tk.Event):
        """key press handler"""
        match event.keysym:
            case "space":
                # This should stop the ui updater, and simply keep the snapshot
                self.controller.snapshot_show()
            case "s" | "S":
                # This should save the ui.
                self.controller.snapshot_show()
                self.after(0, self.controller.save_snapshot)

    def set_controller(self, controller: "Controller"):
        self.controller = controller

    def setup_ui(self):
        """Setup of UI elements"""
        # COM Port Dropdown
        tk.Label(self, text="Select COM Port:").pack(pady=5)

        self.port = ttk.Combobox(self, state="readonly", width=20)
        self.port.pack(pady=5)

        # Baudrate Dropdown
        tk.Label(self, text="Select Baudrate:").pack(pady=5)

        self.baudrate = ttk.Combobox(
            self, values=[9600, 115200], state="readonly", width=20
        )
        self.baudrate.set(115200)
        self.baudrate.pack(pady=5)

        # Number of Samples Dropdown
        tk.Label(self, text="Select Number of samples (per channel):").pack(pady=5)
        self.samples_per_channel = tk.Spinbox(
            self,
            from_=100,
            to=100_000,
            increment=100,
        )
        self.samples_per_channel.pack(pady=20)

        # Connect Button
        self.connect_button = tk.Button(
            self, text="Connect", command=self.on_connect, width=20
        )
        self.connect_button.pack(pady=10)

        # Matplotlib Plot Area (Embedded)
        self.fig, self.ax = plt.subplots()
        self.ax.set_title("Real-time ADC Data")
        self.ax.set_xlabel("Samples")
        self.ax.set_ylabel("ADC Output")
        # self.ax.legend()
        self.lines: list[Line2D] | None = None

        self.canvas = FigureCanvasTkAgg(self.fig, self)
        self.canvas.get_tk_widget().pack(
            pady=10,
            fill="both",
            expand=True,
        )

    def display_data(self, data: pd.DataFrame):
        """Update the graph with new data."""
        named_colors = [
            "blue",
            "green",
            "red",
            "cyan",
            "magenta",
            "yellow",
            "black",
            "white",
            "gray",
            "lightblue",
            "orange",
            "purple",
            "brown",
            "pink",
            "lime",
            "indigo",
            "violet",
            "darkgreen",
            "lightgreen",
            "lightcoral",
            "darkblue",
            "gold",
            "silver",
            "beige",
            "tan",
            "chocolate",
            "seashell",
            "tomato",
            "orchid",
            "salmon",
            "peachpuff",
        ]

        if self.lines is None:
            # Initiate lines in figure
            self.lines = []
            for idx, name in enumerate(data.columns):
                line = Line2D(
                    data.index,
                    data[name],
                    label=name,
                    color=named_colors[idx % len(named_colors)],
                )
                self.lines.append(line)
                self.ax.add_line(line)
            self.ax.legend()
        else:
            # Update the plot
            for idx, name in enumerate(data.columns):
                self.lines[idx].set_xdata(data.index.to_list())
                self.lines[idx].set_ydata(data[name])

        self.ax.relim()  # Recalculate limits
        self.ax.autoscale_view()
        self.canvas.draw()  # Redraw the canvas

    def display_error(self, message: str):
        """Display error messages."""
        tk.messagebox.showerror("Error", message)

    def on_connect(self):
        """Connect to the selected COM port and baudrate."""
        try:
            port = self.port.get()
            baudrate = int(self.baudrate.get())
            samples_per_channel = int(self.samples_per_channel.get())
            if not port:
                raise ValueError("Please select a COM port.")
            if baudrate <= 0:
                raise ValueError("Please select a valid baudrate.")

            self.controller.open_connection(
                port=port, baudrate=baudrate, samples_per_channel=samples_per_channel
            )

        except ValueError as e:
            logger.error(str(e))
            self.display_error(f"Error: {e}")
        except Exception as e:
            logger.error(str(e))
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
        """disable buttons and dropdows,"""
        # activate keybindings
        self.master.bind("<KeyPress>", self.on_key_press)

        # disable buttons
        self.port.config(state="disabled")
        self.baudrate.config(state="disabled")
        self.connect_button.config(state="disabled")
        self.samples_per_channel.config(state="disabled")
