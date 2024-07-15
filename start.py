import tkinter as tk
from tkinter import ttk
import os
from Image import Image
from Atlas import Atlas

class Starter:

    def __init__(self, master):

        self.atlas_name = tk.StringVar()
        atlases = [name for name in os.listdir('Data\\Atlases')]
        atlas_picker_label = ttk.Label(master,text="Atlas:")
        atlas_picker_combo = ttk.Combobox(master,values=atlases, state='readonly',
                                          textvariable=self.atlas_name)
        atlas_picker_combo.set("Choose Atlas")

        self.target_file_name = tk.StringVar()
        target_picker_label = ttk.Label(master,text="Target:")
        target_picker_entry = ttk.Entry(master,textvariable=self.target_file_name)
        target_picker_btn = ttk.Button(master,text="Browse",command=self.select_target)

        start_btn = ttk.Button(master,text="Start!")

        atlas_picker_label.grid(row=0,column=0)
        atlas_picker_combo.grid(row=0,column=1,)
        target_picker_label.grid(row=1,column=0)
        target_picker_entry.grid(row=1,column=1)
        target_picker_btn.grid(row=1,column=2)
        start_btn.grid(row=2,columnspan=3)
    
    def select_target(self):
        file = tk.filedialog.askopenfile(initialdir=os.curdir)
        if file is None: return False # no file selected
        self.target_file_name.set(file.name)
    