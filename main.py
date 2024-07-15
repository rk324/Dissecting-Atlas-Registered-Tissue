import tkinter as tk
from tkinter import ttk
import os
#from Image import Image
#from Atlas import Atlas
from start import Starter

class App:
    def __init__(self):
        root = tk.Tk()
        curr_page = Starter(root)
        root.mainloop()


app = App()
        

'''img = Atlas(root)
img.frame.pack(side=tk.LEFT)
img2 = Image(root)
img2.frame.pack(side=tk.LEFT)
'''
