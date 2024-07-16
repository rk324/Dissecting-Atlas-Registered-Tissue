import tkinter as tk
from tkinter import ttk
import os
from Images import *

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,  
NavigationToolbar2Tk) 

class Page:

    def __init__(self,master):
        self.frame = ttk.Frame(master)
        self.master = master
        
    def activate(self):
        self.frame.grid(row=0,columnspan=2)
    
    def deactivate(self):
        self.frame.grid_remove()
    
    # just in case gets called in a child class that doesnt havea definition for it
    def previous(self): pass
    def next(self): pass

class Starter(Page):

    def __init__(self, master):

        super().__init__(master)

        self.atlas_name = tk.StringVar()
        atlases = [name for name in os.listdir('Data\\Atlases')]
        atlas_picker_label = ttk.Label(self.frame,text="Atlas:")
        atlas_picker_combo = ttk.Combobox(self.frame,values=atlases, state='readonly',
                                          textvariable=self.atlas_name)
        atlas_picker_combo.set("Choose Atlas")

        self.target_file_name = tk.StringVar()
        target_picker_label = ttk.Label(self.frame,text="Target:")
        target_picker_entry = ttk.Label(self.frame,textvariable=self.target_file_name)
        target_picker_btn = ttk.Button(self.frame,text="Browse",command=self.select_target)

        atlas_picker_label.grid(row=0,column=0)
        atlas_picker_combo.grid(row=0,column=1,)
        target_picker_label.grid(row=1,column=0)
        target_picker_entry.grid(row=1,column=1)
        target_picker_btn.grid(row=1,column=2)
    
    def select_target(self):
        file = tk.filedialog.askopenfile(initialdir=os.curdir)
        if file is None: return False # no file selected
        self.target_file_name.set(file.name)
    
    def next(self):

        chosen_atlas = self.atlas_name.get()
        target_address = self.target_file_name.get()

        if chosen_atlas == "Choose Atlas": raise Exception("Please choose an atlas")
        elif target_address == "": raise Exception("Please select a target image file")

        self.deactivate()
        return STalign_Prep(self.master, chosen_atlas, target_address)


class STalign_Prep(Page):
    
    def __init__(self, master, atlas_name, target_address):

        super().__init__(master)
        self.atlas = Atlas(atlas_name)
        self.target = Target(target_address, self.atlas.xA) # TODO: chagne to target class once complete
        
        # rotation scale
        self.rot_scale = ttk.Scale(self.frame, from_=60, to=-60, 
                                   orient='horizontal', length=200,
                                   variable=self.atlas.theta_degrees,
                                   command=self.update) 

        #slice scale
        self.slice_scale = ttk.Scale(self.frame, from_=0, to=self.atlas.img.shape[0]-1,
                                     orient='vertical', length=500, 
                                     variable=self.atlas.curr_slice,
                                     command=self.update)

        # showing images
        self.fig = Figure()
        self.canvas = FigureCanvasTkAgg(self.fig, self.frame)
        self.fig.subplots(1,2)
        self.fig.axes[1].imshow(self.target.get_img())
        self.update()
        
        # add mpl toolbar to allow zoom, translation
        toolbar_frame = ttk.Frame(self.frame)
        toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame) 
        toolbar.update()

        self.rot_scale.grid(row=0, column=1)
        self.slice_scale.grid(row=1, column=0)
        self.canvas.get_tk_widget().grid(row=1, column=1)
        toolbar_frame.grid(row=2, column=1)
    
    def update(self, _=None):
        self.fig.axes[0].imshow(self.atlas.get_img())
        self.canvas.draw()



    