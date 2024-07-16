import tkinter as tk
from tkinter import ttk
import os
from Image import Image
from Atlas import Atlas

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
        atlas = Atlas(atlas_name)


    