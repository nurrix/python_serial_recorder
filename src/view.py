import tkinter as tk
from tkinter import ttk, messagebox
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

COLORS = plt.rcParams["axes.prop_cycle"].by_key()["color"]


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
                    #color=COLORS[idx % len(COLORS)],
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
        """disable buttons and dropdows, and activate keybindings"""
        # activate keybindings
        self.master.bind("<KeyPress>", self.on_key_press)

        # disable buttons
        self.port.config(state="disabled")
        self.baudrate.config(state="disabled")
        self.connect_button.config(state="disabled")
        self.samples_per_channel_spin.config(state="disabled")
