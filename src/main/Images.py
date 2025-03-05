import tkinter as tk
from tkinter import ttk

import nibabel as nib
import nrrd
import numpy as np
import skimage as ski
import PIL
import shapely
import os
import STalign

from constants import DEFAULT_STALIGN_PARAMS

class Image():

    def __init__(self):
        self.pix_dim = None
        self.pix_loc = None
        self.shape = None
        self.img = None

    def load_img(self, img):
        self.img = img
        self.shape = self.img.shape
    
    def set_pix_dim(self, pix_dim):
        if len(pix_dim) != len(self.shape):
            raise Exception(f"""
                Error: pix_dim array has {len(pix_dim)} values, but
                Image instance has {len(self.shape)} dimensions. 
            """)
        self.pix_dim = pix_dim

    def set_pix_loc(self):
        if self.pix_dim is None: 
            raise Exception("Cannot set pix_loc until pix_dim is set")
        self.pix_loc = [np.arange(n)*d - (n-1)*d/2.0 
                        for n,d in zip(self.shape,self.pix_dim)]

    def get_img(self): 
        return self.img.copy()
    
    def get_extent(self):
        return STalign.extent_from_x(self.pix_loc[-2:])

class Atlas(Image):
    
    def slice_from_T (self): # approximate slice
        return int(self.T[0]/self.pix_dim[0] + self.img.shape[0]/2)

    def __init__(self):
        super().__init__()

    def load_img(self, path: str=None, img=None, pix_dim=None, ds_factor=1):
        """
        Atlas implementation of load_img() reads in image data and pixel 
        dimension from provided filename or as parameters. Sets **img**, 
        **pix_dim**, and **shape** properties, and clips and normalizes 
        image data. Can optionally downscale the image using ds_factor

        Currently compatible with nrrd and nifti file types
        """
        if path is None:
            if img is not None and pix_dim is not None:
                self.img = img
                self.pix_dim = pix_dim
            else: raise Exception(f'Invalid parameters provided. Either provide path or provide both img and pix_dim')
        elif path.endswith('.nrrd'): 
            self.img, self.pix_dim = Atlas.load_nrrd(path)
        elif path.endswith(('.nii','.nii.gz')):
            self.img, self.pix_dim = Atlas.load_nii(path)
        else:
            raise Exception(f'File type of {path} not supported.')
        
        self.img =ski.transform.downscale_local_mean(self.img, ds_factor)
        self.pix_dim = ds_factor*self.pix_dim
        self.shape = self.img.shape
        self.img = np.clip(self.img, 0, self.img.max()) # clip negative values
        self.img = (self.img - np.min(self.img)) / (np.max(self.img) - np.min(self.img)) # normalize
        self.set_pix_loc()

    def load_nii(path: str):
        img = nib.load(path)
        
        # ensuring atlas data follows format of slice-row-col indexing
        nii_processor = lambda nii: np.flip(np.transpose(nii.get_fdata(), (1,2,0)), axis=(0,1))
        img_data = nii_processor(img)

        #setting pixdim in microns
        if img.header['xyzt_units'] < 1 or img.header['xyzt_units'] > 3:
            raise Exception("Error: atlas not well formatted")
        pix_multi = 1000**(3-img.header['xyzt_units'])
        pix_dim = np.roll(img.header['pixdim'][1:4],2)*pix_multi
        return img_data, pix_dim
    
    def load_nrrd(path: str):
        img_data, header = nrrd.read(path)
        pix_dim = np.diag(header['space directions'])
        return img_data, pix_dim

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
        
        # Image Estimations using Affine Properties and Atlas
        self.seg_estim = Image()
        self.img_estim = Image()

        # Landmark Points
        self.landmarks = {
            "target": [],
            "atlas": []
        }
        self.num_landmarks = 0
        
        # Initialize Segmentations
        self.seg_stalign = None
        self.seg_visualign = None

    def load_img(self, raw_img_data, pix_dim, ds_factor=1):
        """
        Target implementation of load_img() saves original, downscaled, and 
        preprocess images as **img_original**, **img_donwscaled**, and **img**
        respectively. Also sets pix_dim.
        """
        self.img_original = raw_img_data.copy()
        original_shape = self.img_original.shape

        if ds_factor != 1:
            ds_tuple = tuple([ds_factor if i<2 else 1 
                        for i in range(len(original_shape))])

            self.img_downscaled = ski.transform.downscale_local_mean(
                self.img_original,
                ds_tuple
            )
        else:
            self.img_downscaled = self.img_original.copy()

        self.img = self.img_downscaled.copy()
        if len(original_shape)==3:
            if original_shape[-1]==3:
                self.img = ski.color.rgb2gray(self.img)
            if original_shape[-1]==4:
                self.img = ski.color.rgba2rgb(self.img)
                self.img = ski.color.rgb2gray(self.img)

        # invert colors if less pixels at full intensity than at 0
        if np.count_nonzero(self.img>=.9) > np.count_nonzero(self.img<=0.1):
            print('inverting colors')
            self.img = 1-self.img

        self.pix_dim = pix_dim
        self.shape = self.img.shape
        if self.pix_dim is not None:
            self.set_pix_loc()

    def estimate_pix_dim(self, threshold):
        """
        Estimates **pix_dim** by determining area of tissue in 
        **img_estim** and in **img**. The ratio between these
        areas is the square of the ratio between their **pix_dim**s. Since
        **pix_dim** of the atlas is known, the target's **pix_dim** can be
        estimated.
        """

        # contour function returns contour of the tissue
        def contour (image):
            contours = ski.measure.find_contours(image, threshold)
            return sorted(contours, key=lambda c: shapely.Polygon(c).area)[-1]
        
        # create contour of in both images
        contour_target = contour(self.img)
        contour_atlas = contour(self.img_estim.get_img())

        # get areas of contours
        area_target = shapely.Polygon(contour_target).area
        area_atlas = shapely.Polygon(contour_atlas).area

        scale = np.sqrt(area_target / area_atlas)
        return np.divide(self.img_estim.pix_dim, scale)

    def get_img(self, estimate=True, color=(255,255,255), mode='thick'):
        """
        Target implementation of get_img(), used exclusively to get target
        image with all region boundaries marked. Client can request the
        estimated (before stalign and visualign) marked image or the
        aligned (after stalign and visualign) marked image using the
        **estimate** parameter.
        """
        if estimate:
            image = self.img_estim.get_img()
            segmentation = self.seg_estim.get_img()
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
        self.num_landmarks += 1
    
    def remove_landmarks(self):
        if self.num_landmarks > 0:
            self.landmarks['target'].pop(-1)
            self.landmarks['atlas'].pop(-1)
            self.num_landmarks -= 1
    
    def get_LT(self):
        # thetas follows [z,y,x] format where 'z' represents rotations about the z axis
        L_estim = np.array([[1,0,0],
                            [0,1,0],
                            [0,0,1]])
                            
        L_estim = L_estim@self.x_rot(self.thetas[2])
        L_estim = L_estim@self.y_rot(self.thetas[1])
        L_estim = L_estim@self.z_rot(self.thetas[0])
        return L_estim, self.T_estim
    
    def deg2rad(self, deg):
        return np.pi*deg/180

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


class Slide(Image):

    def __init__(self, filename):
        super().__init__()
        self.load_img(filename)
        self.targets: list[Target] = []
        self.numTargets = 0

        self.calibration_points = []
        self.numCalibrationPoints = 0
        
        self.stalign_params = {
            'timesteps': 12,
            'iterations': 100,
            'sigmaM': 0.5,
            'sigmaP': 1,
            'sigmaR': 1e8,
            'resolution': 250
        }

    def load_img(self, filename):
        self.img = ski.io.imread(filename)
        self.shape = self.img.shape
    
    # resets params if no params passed,
    # if key and val provided, sets given param to given value
    def set_param(self, key=None, val: float =None):    
        if key is None and val is None:
            self.stalign_params = DEFAULT_STALIGN_PARAMS.copy()
        elif key in self.stalign_params:
            self.stalign_params[key] = val
        
    def estimate_pix_dim(self):
        target_pix_dims = [t.estimate_pix_dim() for t in self.targets]
        self.pix_dim = np.average(target_pix_dims, axis=0)
        super().set_pix_loc()
        for t in self.targets:
            t.pix_dim = self.pix_dim
            t.set_pix_loc()

    def add_target(self, x, y, data, ds_factor=1):
        '''
        Creates Target using x,y, and data
        '''
        new_target = Target(data, self.pix_dim, x, y, ds_factor)
        self.targets.append(new_target)
        self.numTargets += 1

    def remove_target(self, index=-1):
        self.targets.pop(index)
        self.numTargets -= 1

    def add_calibration_point(self, point):
        if self.numCalibrationPoints < 3:
            self.calibration_points.append(point)
            self.numCalibrationPoints += 1
        else: raise Exception("Cannot have more than 3 Calibration points")

    def remove_calibration_point(self, index=-1):
        if self.numCalibrationPoints > 0:
            self.calibration_points.pop(index)
            self.numCalibrationPoints -= 1
        else: raise Exception("No Calibration Points to remove")