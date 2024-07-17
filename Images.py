import tkinter as tk
from tkinter import ttk

import nibabel as nib
import nrrd
import numpy as np
import skimage as ski
import os
from scipy.ndimage import rotate
from STalign import STalign

from matplotlib.figure import Figure
from matplotlib.animation import FuncAnimation
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,  
NavigationToolbar2Tk)

class Image():

    def __init__(self, img_name): 
        self.load(img_name)
        self.pix_loc = [np.arange(n)*d - (n-1)*d/2.0 for n,d in zip(self.img.shape,self.pix_dim)]
    
    def load(self, img_name):
        pass

    def get_img(self): return self.img
    def get_extent(self):
        return STalign.extent_from_x(self.pix_loc[-1:-3:-1][::-1])

class Atlas(Image):
    
    def __init__(self, atlas_name):

        super().__init__(atlas_name)

        self.curr_slice = tk.IntVar()
        self.theta_degrees = tk.IntVar()

        self.curr_slice.set(int(self.img.shape[0]/2))
        self.prev_theta = 0
        self.cache_img = self.img[self.curr_slice.get()]

    def load(self, atlas_name):
        # get img and segmentation from folder
        path = f'Data\\Atlases\\{atlas_name}'
        img_list = [f'{path}\\{name}' for name in os.listdir(path)]
        filetype = img_list[0][img_list[0].index('.')+1:] # TODO: find a better way to get file extension

        # file opening based on filetype
        if filetype == 'nii': self.load_nii(img_list)
        elif filetype == 'nrrd': self.load_nrrd(img_list)
        else: raise Exception ("Invalid atlas file type!")
 
    def load_nii(self, img_list):
        img = nib.load(img_list[0])
        labels = nib.load(img_list[1])
        
        # ensuring atlas data follows format of slice-row-col indexing
        nii_processor = lambda nii: np.flip(np.transpose(nii.get_fdata(), (1,2,0)), axis=(0,1))
        self.img = nii_processor(img)
        self.labels = nii_processor(labels)

        #setting pixdim in microns
        if img.header['xyzt_units'] < 1 or img.header['xyzt_units'] > 3:
            raise Exception("Error: atlas not well formatted")
        pix_multi = 1000**(3-img.header['xyzt_units'])
        self.pix_dim = np.roll(img.header['pixdim'][1:4],2)*pix_multi
    
    def load_nrrd(self, img_list):
        self.img,_ = nrrd.read(img_list[0])
        self.labels,hdr = nrrd.read(img_list[1])

        self.pix_dim = np.diag(hdr['space directions'])

    def get_img(self, theta=None):

        if theta is None: theta = self.theta_degrees.get()
        rot_diff = theta-self.prev_theta
        if rot_diff == 0: # changing slice, no reason to use cached img
            return rotate(self.img[self.curr_slice.get()], theta)
        elif rot_diff**2 < theta**2: # faster to rotate cache img
            self.cache_img = rotate(self.cache_img, rot_diff)
        else: # faster to rotate img from theta=0
            self.cache_img = rotate(self.img[self.curr_slice.get()], 
                                    theta)
        return self.cache_img
        
class Target(Image): 

    def __init__(self, filename, src):
        
        self.src_atlas = src
        super().__init__(filename)

    def load(self, filename):
        
        self.pix_dim = self.src_atlas.pix_dim[1:]
        # TODO: rescaling/downscaling image + padding based on how 
        # much of img is the actual slice
        W = ski.color.rgb2gray(ski.io.imread(filename))
        W = (W - np.min(W)) / (np.max(W) - np.min(W)) # normalizing img
        # TODO: add feature to invert colors
        self.img = W