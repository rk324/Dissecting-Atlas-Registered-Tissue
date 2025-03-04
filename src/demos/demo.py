import tkinter as tk
from tkinter import ttk
import sys
import os
sys.path.append(os.path.join('src','main'))

from images import Slide, Atlas
from constants import FSR, DSR, FSL, DSL

class Demo(tk.Tk):

    def __init__(self):
        super().__init__()
        self.widget_frame = tk.Frame(self)
        self.checkpoint_btn = ttk.Button(
            master=self,
            text='Done',
            command = self.done
        )
        self.slides: list[Slide] = []
        self.atlases = {
            FSR: Atlas(),
            DSR: Atlas(),
            FSL: Atlas(),
            DSL: Atlas(),
            'names': None
        }

        self.demo_widget = None # in child class, instantiate demo_widget
    
    def run(self):
        self.widget_frame.pack()
        self.checkpoint_btn.pack()
        self.demo_widget.activate()
        self.mainloop()

    def done(self):
        self.demo_widget.done()
