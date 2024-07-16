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
        self.pages = [Starter(self.root)] # TODO: add more pages
        self.curr_page_idx = 0
        
        self.prev_btn = ttk.Button(self.root,text="Previous", command=self.prev_pg)
        self.nxt_btn = ttk.Button(self.root,text="Next", command=self.nxt_pg)

    def start(self):
        self.update()
        self.root.mainloop()
    
    def nxt_pg(self):
        nxt_pg = self.pages[self.curr_page_idx].next()
        self.curr_page_idx += 1
        self.pages.append(nxt_pg)
        self.update()

    def prev_pg(self):

        self.pages[self.curr_page_idx].frame.destroy()
        self.pages.pop(self.curr_page_idx)
        self.curr_page_idx -= 1
        self.update()
    
    def update(self):
        self.pages[self.curr_page_idx].activate()
        
        # logic for showing next and previous buttons
        self.prev_btn.grid(row=1,column=0)
        self.nxt_btn.grid(row=1,column=1)
        if self.curr_page_idx == 0:
            self.prev_btn.grid_remove()
        elif self.curr_page_idx == 4:
            self.nxt_btn.grid_remove()


# Actually run the app
app = App()
app.start()
