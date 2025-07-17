import tkinter as tk
from tkinter import ttk
import sys
import os
import pickle
sys.path.append(os.path.join('src','main'))

from images import Slide, Atlas
from constants import FSR, DSR, FSL, DSL

class Demo(tk.Tk):

    def __init__(self):
        super().__init__()
        self.widget_frame = tk.Frame(self)
        self.checkpoint_btn = ttk.Button(
            master=self,
            text='Finish & Save Checkpoint',
            command = self.done
        )

        self.project = {}
        self.project['slides'] = []
        self.project['atlases'] = {
            FSR: Atlas(),
            DSR: Atlas(),
            FSL: Atlas(),
            DSL: Atlas(),
            'names': None
        }
        self.project['folder'] = None

        self.path_checkpoints = os.path.join("src", "page_demos", "checkpoints")

        ### OVERRIDE IN CHILD ###
        self.demo_widget = None # in child class, instantiate demo_widget
        self.checkpoint_name = 'post_demo.pkl'
    
    def createDemoWidget(self, widget_class):
        self.demo_widget = widget_class(self.widget_frame, self.project)

    def run(self):
        self.widget_frame.pack(expand=True, fill=tk.BOTH)
        self.checkpoint_btn.pack()
        self.demo_widget.activate()
        self.mainloop()

    def load(self, checkpoint):
        with open(os.path.join(self.path_checkpoints, checkpoint), 'rb') as f:
            data = pickle.load(f)
            self.slides = data['slides']
            self.atlases = data['atlases']

    def done(self):
        self.demo_widget.done()
        data = {"slides": self.project['slides'], "atlases": self.project['atlases']}
        with open(os.path.join(self.path_checkpoints, self.checkpoint_name), 'wb') as f:
            pickle.dump(data, f)
        self.destroy()
