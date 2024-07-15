import tkinter as tk
from tkinter import ttk

import nibabel as nib
import nrrd
import numpy as np
import os
from scipy.ndimage import rotate
from STalign import STalign

from matplotlib.figure import Figure
from matplotlib.animation import FuncAnimation
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,  
NavigationToolbar2Tk) 

'''
Atlas class for displaying atlas

### fields ###
frame: the frame containing image, dropdown, etc

__img: img data

__labels: img segmentation data, stores brain region of each pixel of __img

load_atlas_combo: drop down list for selecting atlas

load_btn: button for loading image data, hidden after image chosen

curr_slice: the current slice of the slice being shown

theta_degrees: angle of rotation of atlas in xy plane

### functions ###
__init__: createsframe to hold everything, load & display atlas if name provided

load: loads atlas data based on user selection from dropdown

display: displays atlas
'''
class Atlas():

    curr_slice = 0
    theta_degrees = 0

    '''
    Initialize with master frame and optional atlas name.
    Create drop down and load button for selecting atlas.
    Load and display atlas if name provided.
    '''
    def __init__(self, master, atlas_name=None):
        self.frame = ttk.Frame(master=master)

        atlases = [name for name in os.listdir('Data\\Atlases')]
        
        self.load_atlas_combo = ttk.Combobox(self.frame,values=atlases, state='readonly')
        self.load_atlas_combo.set("Choose Atlas")
        self.load_atlas_combo.pack()

        self.load_btn = ttk.Button(self.frame, text="Load data", command=self.load)
        self.load_btn.pack()
        
        if atlas_name is not None: self.load(atlas_name)

    '''
    Load atlas data using atlas name, then call display()
    Different file loading methods depending on file type of atlas
    Allows user to upload their own atlases (as long as file type supported)
    '''
    def load(self):
        atlas_name = self.load_atlas_combo.get()
        if atlas_name == "Choose Atlas": return # return if no atlas selected

        # get img and segmentation from folder
        path = f'Data\\Atlases\\{atlas_name}'
        img_list = [f'{path}\\{name}' for name in os.listdir(path)]
        filetype = img_list[0][img_list[0].index('.')+1:]

        # file opening based on filetype
        if filetype == 'nii':

            nii_img = nib.load(img_list[0])
            
            #setting pixdim in microns
            if nii_img.header['xyzt_units'] < 1 or nii_img.header['xyzt_units'] > 3:
                raise Exception("Error: atlas not well formatted")
            pix_multi = 1000**(3-nii_img.header['xyzt_units'])
            dxA = np.roll(nii_img.header['pixdim'][1:4],2)*pix_multi

            # loading img data
            self.__img = nib.load(img_list[0]).get_fdata()
            self.__img = np.flip(np.transpose(self.__img, (1,2,0)), axis=(0,1))
            #loading segmentation data
            self.__labels = nib.load(img_list[1]).get_fdata()
            self.__labels = np.flip(np.transpose(self.__img, (1,2,0)), axis=(0,1))
            # TODO: smth to do with the dxA, nxA, other stuff like that
        if filetype == 'nrrd':
            self.__img,_ = nrrd.read(img_list[0])
            self.__labels,hdr = nrrd.read(img_list[1])

            dxA = np.diag(hdr['space directions'])

        self.curr_slice = int(self.__img.shape[0]/2)
        self.xA = [np.arange(n)*d - (n-1)*d/2.0 for n,d in zip(self.__img.shape,dxA)]
        
        
        self.display()
        self.load_btn.pack_forget()
        self.load_atlas_combo.pack_forget()
    
    '''
    Display image data using matplotlib
    '''
    def display(self):
        # rotation scale
        self.rot_scale = tk.Scale(self.frame, from_=60, to=-60,
                                  orient='horizontal', length=200,
                                  command=self.update) 
        self.rot_scale.pack()

        #slice scale
        self.slice_scale = tk.Scale(self.frame, from_=0, to=self.__img.shape[0]-1,
                                     orient='vertical', length=500, showvalue=False,
                                     command=self.update)
        self.slice_scale.set(self.curr_slice)
        self.slice_scale.pack(side=tk.LEFT)

        self.fig = Figure()
        self.canvas = FigureCanvasTkAgg(self.fig, self.frame)
        self.fig.add_subplot(111)
        self.update()
        
        # add mpl toolbar to allow zoom, translation
        toolbar = NavigationToolbar2Tk(self.canvas, self.frame) 
        toolbar.update() 

        self.canvas.get_tk_widget().pack(side=tk.RIGHT)
    
    '''
    Updates image shown based on theta and slice selections
    '''
    def update(self, _=None):
        self.theta_degrees = int(self.rot_scale.get())
        self.curr_slice = int(self.slice_scale.get())

        self.fig.axes[0].imshow(rotate(self.__img[self.curr_slice], self.theta_degrees))
        self.canvas.draw()
        

