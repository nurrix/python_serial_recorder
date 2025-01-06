import tkinter as tk
import logging

from controller import Controller
from models import Model
from views import View




def on_close(model: Model, view: View, root: tk.Toplevel) -> None:
    model.close_connection()  # close serial connection
    view.destroy()
    root.quit()


def main() -> None:
    # Create the Tkinter root window
    name = "Serial Data Viewer"
    root: tk.Toplevel = tk.Tk(screenName=name, baseName=name, className=name)
    root.geometry(f"{int(root.winfo_screenwidth() // 2)}x{int(root.winfo_screenheight() // (3/2))}")

    # Create UI using the MVC pattern (Model, View, Controller)
    model = Model()  # Model only knows about data
    view = View(master=root)
    controller = Controller(model, view, update_rate_ms=100)
    view.set_controller(controller=controller)  # View only knows about controller

    # Set a close script, using the WM_DELETE_WINDOW protocol
    root.protocol(
        "WM_DELETE_WINDOW",
        lambda: on_close(model=model, view=view, root=root),  # noqa: F821
    )

    # Start the Tkinter event loop
    root.mainloop()


if __name__ == "__main__":
    # Set up basic configuration for logging
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logger = logging.getLogger(__name__)
    logger.info("Starting Serial Recorder...")
    main()
    logger.info("Exititing...")
