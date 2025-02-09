import tkinter as tk
from tkinter import ttk

import nibabel as nib
import nrrd
import numpy as np
import skimage as ski
import os
from scipy.ndimage import rotate
import STalign

from matplotlib.figure import Figure
from matplotlib.animation import FuncAnimation
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,  
NavigationToolbar2Tk)

from abc import ABC, abstractmethod

class Image(ABC):

    def __init__(self):
        self.pix_dim = None
        self.pix_loc = None
        self.shape = None
    
    @abstractmethod
    def load_img(self):
        """
        Image implementation of load_img() sets **shape** and **pix_loc** properties.
        Assumes **img** and **pix_dim** properties have already been defined.
        """
        self.shape = self.img.shape
        self.pix_loc = [np.arange(n)*d - (n-1)*d/2.0 
                        for n,d in zip(self.shape,self.pix_dim)]
        pass

    @abstractmethod
    def get_img(self): 
        return self.img.copy()
    
    def get_extent(self):
        return STalign.extent_from_x(self.pix_loc[-2:])

class Atlas(Image):
    
    def slice_from_T (self): # approximate slice
        return int(self.T[0]/self.pix_dim[0] + self.img.shape[0]/2)

    def __init__(self):
        super().__init__()
        self.img = None

    def load_img(self, img_data, pix_dim):
        """
        Atlas implementation of load_img() sets **img** and **pix_dim** properties,
        and clips and normalizes image data.
        """
        self.img = img_data
        self.pix_dim = pix_dim
        self.img = np.clip(self.img, 0, self.img.max()) # clip negative values
        self.img = (self.img - np.min(self.img)) / (np.max(self.img) - np.min(self.img)) # normalize
        super().load_img()

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

    def get_img(self, sample_mesh):
        return STalign.interp3D(
            self.pix_loc, 
            self.img[None].astype('float64'), 
            sample_mesh.transpose(3,0,1,2)
            )[0,0,...].numpy()
        
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

    def __init__(self, img_data, pix_dim, x, y, ds_factor=1):
        super().__init__()
        self.load_img(img_data, pix_dim, ds_factor)

        # Location properties
        self.x_offset = x
        self.y_offset = y

        # Affine Estimation Properties
        self.thetas = np.array([0, 0, 0]) # z, y, x order
        self.T_estim = np.array([0, 0, 0]) # z, y, x order 
        self.L_estim = np.eye(3)
        
        # Image Estimations using Affine Properties and Atlas
        self.seg_estim = None
        self.img_slice_estim = None

        # Landmark Points
        self.landmarks = {
            "target": [],
            "atlas": []
        }
        
        # Initialize Segmentations
        self.seg_stalign = None
        self.seg_visualign = None

    def load_img(self, raw_img_data, pix_dim, ds_factor):
        """
        Target implementation of load_img() saves original, downscaled, and 
        preprocess images as **img_original**, **img_donwscaled**, and **img**
        respectively. Also sets pix_dim.
        """
        self.img_original = raw_img_data.copy()
        original_shape = self.img_original.shape
        ds_tuple = (ds_factor if i<2 else 1 
                    for i in range(len(original_shape)))

        self.img_downscaled = ski.transform.downscale_local_mean(
            self.img_original,
            ds_tuple
        )

        self.img = self.img_downscaled.copy()
        if len(original_shape)==3:
            if original_shape[-1]==3:
                self.img = ski.color.rgb2gray(self.img)
            if original_shape[-1]==4:
                self.img = ski.color.rgba2rgb(self.img)
                self.img = ski.color.rgb2gray(self.img)

        # invert colors if more pixels at full intensity than at 0
        if np.count_nonzero(self.img==1) > np.count_nonzero(self.img==0):
            self.img = 1-self.img

        self.pix_dim = pix_dim
        super().load_img()

    def get_img(self, estimate=True, color=(255,255,255), mode='thick'):
        """
        Target implementation of get_img(), used exclusively to get target
        image with all region boundaries marked. Client can request the
        estimated (before stalign and visualign) marked image or the
        aligned (after stalign and visualign) marked image using the
        **estimate** parameter.
        """
        if estimate:
            image = self.img_slice_estim
            segmentation = self.seg_estim
        else:
            image = self.img_downscaled
            segmentation = self.seg_visualign
        
        if image is None or segmentation is None: return None
        else:
            return ski.segmentation.mark_boundaries(
                image,
                segmentation.astype('int'),
                color=color,
                mode=mode,
                background_label=0
            )

    def add_landmarks(self, target_point, atlas_point):
        self.landmarks['target'].append(target_point)
        self.landmarks['atlas'].append(atlas_point)

class Slide(Image):

    def __init__(self, img_data, pix_dim):
        super().init()
        self.load_img(img_data, pix_dim)
        self.targets: list[Target] = []
        self.num_targets = 0

        self.calibration_points = []
        
        self.stalign_params = {
            'timesteps': 12,
            'iterations': 100,
            'sigmaM': 0.5,
            'sigmaP': 1,
            'sigmaR': 1e8,
            'resolution': 250
        }

    def load_img(self, img_data, pix_dim):
        self.img = img_data
        self.pix_dim = pix_dim
        super().load_img()
    
    def add_target(self, x, y, height, width, ds_factor=1):
        '''
        Creates Target and adds to **targets** by cropping image 
        data with top-left corner coordinates specified by **x** 
        and **y** and with dimensions specified by **height** and 
        **width**
        '''
        img_data = self.img[y : y+height, x : x+width]
        new_target = Target(img_data, self.pix_dim, x, y, ds_factor)
        self.targets.append(new_target)
        self.num_targets += 1

               