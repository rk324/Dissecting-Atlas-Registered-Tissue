import tkinter as tk
from tkinter import ttk
import sys
import os
sys.path.append(os.path.join('src','main'))

from images import Slide, Atlas
from constants import FSR, DSR, FSL, DSL
from pages import Starter

root = tk.Tk()
slides: list[Slide] = []
atlases = {
    FSR: Atlas(),
    DSR: Atlas(),
    FSL: Atlas(),
    DSL: Atlas(),
    'names': None
}


demo = Starter(root, slides, atlases)
demo.activate()
root.mainloop()