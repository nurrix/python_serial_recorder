import tkinter as tk
from controller import SerialController
from models import SerialModel
from views import SerialApp
import logging
import sys

# Set up basic configuration for logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


logger = logging.getLogger(__name__)

def main():
    # Create the Tkinter root window
    root : tk.Toplevel = tk.Tk()
    root.title("Serial Data Viewer")
    view = SerialApp(master=root)
    model = SerialModel()
    controller = SerialController(model, view)
    view.set_controller(controller=controller)

    logger.info("Running root.mainloop()...")
    # Create the model, view, and controller
    # Start the Tkinter event loop
    root.mainloop()
    
    

if __name__== "__main__":
    logger.info("Starting...")
    main()
    logger.info("Exititing...")
    sys.exit()
    
    