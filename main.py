import tkinter as tk
from tkinter import ttk
import os
#from Image import Image
#from Atlas import Atlas
from Pages import *
from abc import ABC

class App:
    def __init__(self):
        self.root = tk.Tk()
        self.pages = [Starter(self.root)]
        self.curr_page_idx = 0
        
        self.prev_btn = ttk.Button(self.root,text="Previous")
        self.nxt_btn = ttk.Button(self.root,text="Next")
        self.prev_btn.grid(row=1,column=0)
        self.nxt_btn.grid(row=1,column=1)

    
    def start(self):
        self.pages[self.curr_page_idx].activate()
        self.root.mainloop()
        


app = App()
app.start()
