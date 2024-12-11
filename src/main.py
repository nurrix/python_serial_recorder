import tkinter as tk
from controller import SerialController
from models import SerialModel
from views import SerialApp


# Create the Tkinter root window
root = tk.Tk()
root.withdraw()
view = SerialApp(master=root)
model = SerialModel()
controller = SerialController(model, view)
view.set_controller(controller=controller)

# Create the model, view, and controller
# Start the Tkinter event loop
root.mainloop()
