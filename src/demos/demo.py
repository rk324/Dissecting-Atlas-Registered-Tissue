import tkinter as tk
from tkinter import ttk
import sys
import os
sys.path.append(os.path.join('src','main'))

from images import Slide, Atlas
from constants import FSR, DSR, FSL, DSL
from pages import Starter

class Demo():

    def __init__(self):
        self.root = tk.Tk()
        self.widget_frame = tk.Frame(self.root)
        self.checkpoint_btn = ttk.Button(
            master=self.root,
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

        self.demo_widget = None
    
    def run(self):
        self.widget_frame.pack()
        self.checkpoint_btn.pack()
        self.demo_widget.activate()
        self.root.mainloop()

    def done(self):
        self.demo_widget.done()
        # save slides, atlases in pickle
