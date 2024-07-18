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
        self.shape = self.img.shape
        self.pix_loc = [np.arange(n)*d - (n-1)*d/2.0 for n,d in zip(self.shape,self.pix_dim)]
        print(f'uploaded img w shape {self.shape}')
    
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
        self.ds_factor = int(np.max(np.divide(self.shape[1:], [200, 300])))
        if self.ds_factor == 0: self.ds_factor = 1

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

    def get_img(self, theta=None, quickReturn=True):

        if theta is None: theta = self.theta_degrees.get()
        if not quickReturn: return rotate(self.img[self.curr_slice.get()], theta) # returns full atlas img

        # quick return will return downscaled img (makes rotation faster)
        return rotate(ski.transform.downscale_local_mean(self.img[self.curr_slice.get()],
                                                         (self.ds_factor, self.ds_factor)), 
                                                         theta)
        
class Target(Image): 

    def __init__(self, filename, src):
        
        self.src_atlas = src
        super().__init__(filename)

    def load(self, filename):
        
        self.pix_dim = self.src_atlas.pix_dim[1:]
        # TODO: rescaling/downscaling image + padding based on how 
        # much of img is the actual slice
        W = ski.io.imread(filename)
        if len(W.shape)==3 and W.shape[-1]==3:
            W = ski.color.rgb2gray(W)
        for _ in range(len(W.shape)-2): W = W[0] # eliminating extra channels (assuming relavant information is in last two axes)
        
        if np.count_nonzero(W==1) > np.count_nonzero(W==0): W = 1-W

        ds_factor = int(np.max(W.shape) / np.max(self.src_atlas.shape))
        if ds_factor == 0: ds_factor = 1
        W = ski.transform.downscale_local_mean(W, (ds_factor, ds_factor))

        W = (W - np.min(W)) / (np.max(W) - np.min(W)) # normalizing img

        self.img = W