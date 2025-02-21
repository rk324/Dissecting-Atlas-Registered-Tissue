import tkinter as tk
from tkinter import ttk
import sys
import os
sys.path.append(os.path.join('src','main'))

from images import Slide, Atlas
from constants import FSR, DSR, FSL, DSL
from pages import Starter, SlideProcessor
print('hello')

root = tk.Tk()
slides: list[Slide] = []
atlases = {
    FSR: Atlas(),
    DSR: Atlas(),
    FSL: Atlas(),
    DSL: Atlas(),
    'names': None
}

starter = Starter(root, slides, atlases)
starter.load_atlas_info(os.path.join('atlases','allen_nissl_100um'))
starter.load_slides('demo_images')
demo = SlideProcessor(root, slides, atlases)
demo.activate()
root.mainloop()