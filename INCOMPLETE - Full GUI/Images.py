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
    
    
    def slice_from_T (self): # approximate slice
        return int(self.T[0]/self.pix_dim[0] + self.img.shape[0]/2)

    def __init__(self, atlas_name):

        super().__init__(atlas_name)
        self.deg2rad = lambda deg: np.pi*deg/180 # converting degrees to radians

        self.curr_slice = tk.IntVar()
        self.thetas = [tk.IntVar() for i in range(3)] #3 thetas for yaw, pitch, roll

        self.set_LT()
        self.origin_slice = np.stack(np.meshgrid(np.zeros(1),
                                                 1.5*self.pix_loc[1],
                                                 1.5*self.pix_loc[2],
                                                 indexing='ij'), -1)
        
        # creating downscaled copies of everything
        dsf = int(np.max(np.divide(self.shape[1:], [200, 300]))) # downscaling factor
        if dsf == 0: dsf = 1
        self.img_ds = ski.transform.downscale_local_mean(self.img, (1, dsf, dsf))
        self.pix_dim_ds = np.multiply(self.pix_dim, [1 ,dsf, dsf])
        self.pix_loc_ds = [np.arange(n)*d - (n-1)*d/2.0 for n,d in zip(self.img_ds.shape,self.pix_dim_ds)]
        self.origin_slice_ds = np.stack(np.meshgrid(np.zeros(1),
                                                 1.5*self.pix_loc_ds[1],
                                                 1.5*self.pix_loc_ds[2],
                                                 indexing='ij'), -1)

    def load(self, atlas_name):
        # get img and segmentation from folder
        path = f'..\\Data\\Atlases\\{atlas_name}'
        img_list = [f'{path}\\{name}' for name in os.listdir(path)]
        filetype = img_list[0][img_list[0].index('.')+1:] # TODO: find a better way to get file extension

        # file opening based on filetype
        if filetype == 'nii': self.load_nii(img_list)
        elif filetype == 'nrrd': self.load_nrrd(img_list)
        else: raise Exception ("Invalid atlas file type!")

        self.img = np.clip(self.img, 0, self.img.max())
        self.img = (self.img - np.min(self.img)) / (np.max(self.img) - np.min(self.img))

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

    def get_img(self, show_seg=True, quickReturn=True):
        
        if not show_seg:
            return self.get_slice_img(quickReturn)
        else:
            seg = self.get_slice_seg(quickReturn)
            img = self.get_slice_img(quickReturn)
            return ski.segmentation.mark_boundaries(img, seg.astype('int'), 
                                                    color=(255,0,0), mode='subpixel', 
                                                    background_label=0)
        
    def get_slice_seg(self, quickReturn=True):
        if quickReturn: 
            sampler = self.origin_slice_ds
        else: 
            sampler = self.origin_slice
        
        vol = self.labels
        xV = self.pix_loc
        transformed_slice = (self.L@sampler[...,None])[...,0] + self.T

        return STalign.interp3D(xV, vol[None].astype('float64'), 
                                transformed_slice.transpose(3,0,1,2),
                                mode='nearest')[0,0,...].numpy()

    def get_slice_img(self, quickReturn=True):

        if quickReturn: 
            sampler = self.origin_slice_ds
            vol = self.img_ds
            xV = self.pix_loc_ds
        else: 
            sampler = self.origin_slice
            vol = self.img
            xV = self.pix_loc
        
        transformed_slice = (self.L@sampler[...,None])[...,0] + self.T
        
        return STalign.interp3D(xV, vol[None].astype('float64'), 
                                transformed_slice.transpose(3,0,1,2))[0,0,...].numpy()
        
    def set_LT(self):
        
        # reset L and T
        self.L = np.array([[1,0,0],
                           [0,1,0],
                           [0,0,1]])
        self.T = np.array([0, 0, 0])   

        # apply rotations and translations
        self.L = self.L@self.x_rot(self.thetas[2].get())
        self.L = self.L@self.y_rot(self.thetas[1].get())
        self.L = self.L@self.z_rot(self.thetas[0].get())
        self.T[0] += self.curr_slice.get()

    def z_rot(self, deg):
        rads = self.deg2rad(deg)
        return np.array([
                            [1,       0     ,       0      ],
                            [0, np.cos(rads), -np.sin(rads)],
                            [0, np.sin(rads), np.cos(rads) ]
                        ])

    def y_rot(self, deg):
        rads = self.deg2rad(deg)
        return np.array([
                            [ np.cos(rads), 0, np.sin(rads)],
                            [        0    , 1,     0       ],
                            [-np.sin(rads), 0, np.cos(rads)]
                        ])

    def x_rot(self, deg):
        rads = self.deg2rad(deg)
        return np.array([
                            [np.cos(rads), -np.sin(rads), 0],
                            [np.sin(rads),  np.cos(rads), 0],
                            [       0      ,        0   , 1]
                        ])

class Target(Image): 

    def __init__(self, filename, src):
        
        self.src_atlas = src
        super().__init__(filename)

    def load(self, filename):
        
        self.pix_dim = self.src_atlas.pix_dim[1:] # TODO: attempt to read this in from meta data -> if not present, promp user
        # TODO: rescaling/downscaling image + padding based on how 
        # much of img is the actual slice
        W = ski.io.imread(filename)
        self.orig_img = W.copy()
        
        if len(W.shape)==3 and W.shape[-1]==3: # grayscale img if rgb
            W = ski.color.rgb2gray(W)
        
        # eliminating extra channels 
        # (assuming relavant information is in last two axes)
        for _ in range(len(W.shape)-2): W = W[0] 
        
        # invert colors if more pixels at full intensity than at 0
        if np.count_nonzero(W==1) > np.count_nonzero(W==0): W = 1-W

        # downscale to general shape of atlas TODO: accomodate for rotation
        ds_factor = int(np.max(W.shape) / np.max(self.src_atlas.shape))
        if ds_factor == 0: ds_factor = 1
        W = ski.transform.downscale_local_mean(W, (ds_factor, ds_factor))

        W = (W - np.min(W)) / (np.max(W) - np.min(W)) # normalizing img

        self.img = W