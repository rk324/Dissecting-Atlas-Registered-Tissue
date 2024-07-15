import tkinter as tk
from tkinter import ttk
import nibabel as nib
import numpy as np
import os
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,  
NavigationToolbar2Tk) 
from Image import Image

class Atlas():

    slice = 0

    def __init__(self, master, atlas_name=None):
        self.__frame = ttk.Frame(master=master)
        self.__frame.pack()

        atlases = [name for name in os.listdir('Data\\Atlases')]
        
        self.load_atlas_combo = ttk.Combobox(values=atlases, state='readonly',
                                             master=self.__frame)
        self.load_atlas_combo.set("Choose Atlas")
        self.load_atlas_combo.pack()

        self.load_btn = ttk.Button(master=self.__frame, text="Load data", command=self.load)
        self.load_btn.pack()
        
        if atlas_name is not None: self.load(atlas_name)

    def load(self):
        
        atlas_name = self.load_atlas_combo.get()
        path = f'Data\\Atlases\\{atlas_name}'
        img_list = [f'{path}\\{name}' for name in os.listdir(path)]
        filetype = img_list[0][img_list[0].index('.')+1:]

        if filetype == 'nii':
            self.__img = nib.load(img_list[0]).get_fdata()
            self.__img = np.flip(np.transpose(self.__img, (1,2,0)), axis=(0,1))
            
            self.__labels = nib.load(img_list[1]).get_fdata()
            self.__labels = np.flip(np.transpose(self.__img, (1,2,0)), axis=(0,1))
            # TODO: smth to do with the dxA, nxA, other stuff like that
        
        self.load_btn.pack_forget()
        self.load_atlas_combo.pack_forget()
        self.slice = int(self.__img.shape[0]/2)
        
        print(self.slice)

        self.display()
    
    def display(self):
        fig = Figure()
        fig.add_subplot(111).imshow(self.__img[self.slice])
        canvas = FigureCanvasTkAgg(fig,master=self.__frame)
        canvas.draw()
        
        # add mpl toolbar to allow zoom, translation
        toolbar = NavigationToolbar2Tk(canvas, self.__frame) 
        toolbar.update() 

        canvas.get_tk_widget().pack()
            
        

