import tkinter as tk
from tkinter import ttk
import sys
import os
sys.path.append('src')
sys.path.append(os.path.join('src', 'main'))


root = tk.Tk()
slides: list[Slide] = []
atlases = {
    FSR: Atlas(),
    DSR: Atlas(),
    FSL: Atlas(),
    DSL: Atlas(),
    'names': None
}


demo = Starter()
demo.activate()
root.mainloop()