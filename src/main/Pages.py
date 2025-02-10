import tkinter as tk
from tkinter import ttk
import os
from images import *
from constants import *
import torch
import shapely
import pandas as pd
from sklearn.cluster import dbscan

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,  
NavigationToolbar2Tk)

from abc import ABC, abstractmethod

import pickle #TODO: remove if not using anymore

class Page(tk.Frame, ABC):

    def __init__(self, master, slides, atlases):
        super().__init__(master)

        self.slides = slides
        self.atlases = atlases
        self.header = ""
        self.create_widgets()
        self.show_widgets()

    @abstractmethod
    def create_widgets(self): pass

    @abstractmethod
    def show_widgets(self): pass

    def create_figure(self, num_rows, num_cols):
        
        # create plots with specified dimensions
        self.fig = Figure()
        self.canvas = FigureCanvasTkAgg(self.fig, self.frame)
        self.fig.subplots(num_rows, num_cols)

        # add mpl toolbar to allow zoom, translation
        self.toolbar_frame = ttk.Frame(self.frame)
        toolbar = NavigationToolbar2Tk(self.canvas, self.toolbar_frame) 
        toolbar.update()

    def activate(self):
        self.pack(expand=True, fill=tk.BOTH)
    
    def deactivate(self):
        self.pack_forget()
    
    @abstractmethod
    def done(self):
        self.deactivate()

    @abstractmethod
    def cancel(self):
        self.deactivate()

    def get_header(self):
        return self.header

    # just in case gets called in a child class that doesnt have a definition for it
    def previous(self): pass
    def next(self): pass

class Starter(Page):

    def __init__(self, master, slides, atlases):

        super().__init__(master, slides, atlases)
        self.header = 'Select samples and atlas'
        self.create_widgets()
        self.show_widgets()
    
    def create_widgets(self):
        # Atlas Picker
        self.atlas_name = tk.StringVar(master=self, value="Choose Atlas")
        atlases = os.listdir(r'atlases')
        self.atlas_picker_label = ttk.Label(self, text="Atlas:")
        self.atlas_picker_combobox = ttk.Combobox(
            master=self, 
            values=atlases,
            state='readonly',
            textvariable=self.atlas_name
        )

        # Slides Picker
        self.slides_folder_name = tk.StringVar(master=self)
        self.slides_picker_label = ttk.Label(self, text="Samples:")
        self.slides_picker_entry = ttk.Entry(
            master=self,
            textvariable=self.slides_folder_name
        )
        self.browse_button = ttk.Button(
            master=self,
            text="Browse",
            command=self.select_slides
        )

    def show_widgets(self):

        # configure columns
        self.grid_columnconfigure(0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2)

        # show widgets using grid()
        self.atlas_picker_label.grid(row=0, column=0)
        self.atlas_picker_combobox.grid(row=0, column=1, sticky='ew')
        self.slides_picker_label.grid(row=1, column=0)
        self.slides_picker_entry.grid(row=1, column=1, sticky='ew')
        self.browse_button.grid(row=1, column=2)
    
    def select_slides(self):
        folder_name = tk.filedialog.askdirectory(
            parent=self, 
            initialdir=os.curdir,
            mustexist=True
        )
        self.slides_folder_name.set(folder_name)
    
    def cancel(self):
        super().cancel()

    def done(self):
        pass

    def next(self):

        chosen_atlas = self.atlas_name.get()
        target_address = self.target_file_name.get()

        if chosen_atlas == "Choose Atlas": raise Exception("Please choose an atlas")
        elif target_address == "": raise Exception("Please select a target image file")

        self.deactivate()
        return STalign_Prep(self)

class STalign_Prep(Page):
    
    def __init__(self, prev):

        super().__init__(prev.master)
        atlas_name = prev.atlas_name.get()
        target_address = prev.target_file_name.get()

        self.header = 'Select slice and estimate rotations using sliders.'
        self.atlas = Atlas(atlas_name)
        self.target = Target(target_address, self.atlas)

        
        # rotation scales
        self.rot_scales = ttk.Frame(self.frame)
        self.zrot_scale = ttk.Scale(self.rot_scales, from_=180, to=-180, 
                                   orient='vertical', length=500,
                                   variable=self.atlas.thetas[0],
                                   command=self.update) 
        self.yrot_scale = ttk.Scale(self.rot_scales, from_=180, to=-180, 
                                   orient='vertical', length=500,
                                   variable=self.atlas.thetas[1],
                                   command=self.update) 
        self.xrot_scale = ttk.Scale(self.rot_scales, from_=180, to=-180, 
                                   orient='vertical', length=500,
                                   variable=self.atlas.thetas[2],
                                   command=self.update)
        self.zrot_scale.pack(side=tk.LEFT)
        self.yrot_scale.pack(side=tk.LEFT)
        self.xrot_scale.pack(side=tk.LEFT)

        #slice scale
        self.slice_scale = ttk.Scale(self.frame, from_=self.atlas.pix_loc[0][0], 
                                     to=self.atlas.pix_loc[0][-1],
                                     orient='horizontal', length=500, 
                                     variable=self.atlas.curr_slice,
                                     command=self.update)

        # show images
        self.create_figure(1,2)
        self.fig.axes[1].imshow(self.target.get_img())
        self.update()

        self.slice_scale.grid(row=0, column=1)
        self.rot_scales.grid(row=1, column=0)
        self.canvas.get_tk_widget().grid(row=1, column=1)
        self.toolbar_frame.grid(row=2, column=1)

    def update(self, _=None):
        self.atlas.set_LT() # set L and T based on scales
        self.fig.axes[0].cla()
        self.fig.axes[0].imshow(self.atlas.get_img(False,True)) # get img, without segmentation and quickly
        self.fig.canvas.draw_idle()
    
    def next(self):
        self.deactivate()
        return Landmark_Annotator(self)

class Landmark_Annotator(Page):

    def __init__(self, prev):
        super().__init__(prev.master)

        # controls
        self.header = '''Mark atlas-target point pairs one pair at a time and submit each pair before marking the next! Click 'Next' to move on
        
        Controls:
        L-click\tmark point
        R-click\tremove point
        Enter\tsubmit point
        Backspace\tdelete last submitted
        Dbl L-click\ttoggle segmentation'''

        self.atlas = prev.atlas
        self.target = prev.target

        # Get slice images without and with segmentation, full quality (quickReturn=False)
        self.slice_img = self.atlas.get_img(False, False)
        self.slice_seg = self.atlas.get_img(True, False)
        self.show_seg = False

        self.imgs = [self.slice_img, self.target.get_img()]
        self.extents = [self.atlas.get_extent(), self.target.get_extent()]
        self.points = [ [], [] ] # landmark points, points[0][i] in atlas corresponds with points[1][i] in target
        self.new_pt = [ [], [] ]
        self.pt_sz = 4
    
        #show images
        self.create_figure(1,2)
        self.update()

        self.canvas.get_tk_widget().grid(row=0, column=0)
        self.toolbar_frame.grid(row=1, column=0)

        self.canvas.mpl_connect('button_press_event', self.onclick)
        self.canvas.mpl_connect('key_press_event',self.onpress)
        self.canvas.get_tk_widget().bind('<Double-1>',self.ondouble)


    def update(self, axis=None):

        if axis is None:
            self.update(0)
            self.update(1)
            return
        elif axis not in [0,1]: 
            raise Exception(f"Bad call to Landmark_Annotator.update(axis={axis})")

        self.fig.axes[axis].cla()
        self.fig.axes[axis].imshow(self.imgs[axis], extent=self.extents[axis])
        
        # plot prev selected points in white
        if len(self.points[0]): 
            self.fig.axes[axis].scatter(np.array(self.points)[axis,:,1],
                                        np.array(self.points)[axis,:,0], 
                                        color='white', s=self.pt_sz)
        # plot current new point in red
        if len(self.new_pt[0]):
            print(self.new_pt)
            self.fig.axes[axis].scatter(self.new_pt[axis][1],self.new_pt[axis][0], 
                                        color='red', s=self.pt_sz)


        self.canvas.draw()
    
    def ondouble(self, event):
        self.show_seg = not self.show_seg # toggle show_seg
        if self.show_seg: 
            self.imgs[0] = self.slice_seg
            print("showing segmentation")
        else: 
            self.imgs[0] = self.slice_img
            print("hiding segmentation")
        self.update(0)

    def onclick(self, event):
        if event.xdata == None: return # clicked outside of axes
        ix, iy = int(event.xdata), int(event.ydata) # get x and y data of pt
        msg = ''
        
        axis = -1
        # based on where user clicked, set axis and update output msg
        if event.inaxes == self.fig.axes[0]: # user clicked atlas
            axis = 0
            msg = "source at " + msg
        elif event.inaxes == self.fig.axes[1]: # user clicked target
            axis = 1
            msg = "target at " + msg
        else: print("ERROR: clicked outside axes")
    
        if event.button == 1: # left click means add point at mouse location
            #self.fig.axes[axis].scatter([ix],[iy], color='red', s=self.pt_sz)
            self.new_pt[axis] = [iy, ix]
            msg = 'point added to ' + msg + f'[x,y]=[{ix},{iy}]'
        elif event.button == 3: # right click means remove previously created point
            msg = 'point removed from ' + msg + f'[x,y]={self.new_pt[axis][::-1]}'
            self.new_pt[axis] = []

        self.update(axis)
        print(msg)

    def onpress(self, event):
        if event.key == 'enter': # enter key used to commit selected points to points list

            if not len(self.new_pt[0])*len(self.new_pt[1]): # if missing a point in either axis, throw error
                print("ERROR: attempted landmark save with one or more points missing!")
                return

            # add new points to list, notify user, and clear out new points list
            self.points[0].append(self.new_pt[0])
            self.points[1].append(self.new_pt[1])
            print(f"Added {self.new_pt[0][::-1]} and {self.new_pt[1][::-1]} to points list")
            self.new_pt[0] = []
            self.new_pt[1] = []
            self.update()
        
        if event.key == 'backspace': # backspace key used to remove recently committed point
            if len(self.points[0]) == 0: return # if no points to remove, simply return
            print(f'Removed [{self.points[0][-1][::-1]}] and [{self.points[1][-1][::-1]}]') # user msg
            
            # remove last pair of poins
            self.points[0].pop(-1)
            self.points[1].pop(-1)
            self.update() # refresh both axes

    def next(self):
        self.deactivate()
        return STalign_Runner(self)
    
class STalign_Runner(Page):

    def __init__(self, prev):
        super().__init__(prev.master)
        self.header='''Enter desired parameters. Recommended parameters loaded. Click 'Start' when ready

        nt: Number of timesteps for integrating velocity field
        niter: Number of iterations of gradient descent optimization
        epL: Gradient descent step size for linear part of affine
        epT: Gradient descent step size of translation part of affine
        epV: Gradient descent step size for velocity field
        sigmaM: Controls matching accuracy with smaller corresponding to more accurate. 
        sigmaR: Standard deviation for regularization- Smaller means smoother transformation
        sigmaP: Standard deviation for matching of points
        a: Smoothness scale of velocity field
        '''
        self.run_complete = False

        self.atlas = prev.atlas
        self.target = prev.target
        self.points = prev.points

        W = self.target.img
        A = self.atlas.img # TODO: add feature to enable quick run wherein we use downsampled atlas and target
        xI = self.atlas.pix_loc
        xJ = self.target.pix_loc
        slice = self.atlas.curr_slice.get()

        scale_x = 1
        scale_y = 1
        scale_z = 1

        # set device if cuda if possible
        self.device = 'cpu'
        if torch.cuda.is_available(): self.device = 'cuda'

        self.J = W[None] / np.mean(np.abs(W))
        self.I = A[None] / np.mean(np.abs(A), keepdims=True)
        self.I = np.concatenate((self.I, (self.I - np.mean(self.I))**2))

        scale_matrix = np.diagflat([scale_z, scale_y, scale_x])
        self.T = -self.atlas.T
        self.L = np.linalg.inv(self.atlas.L)

        int_checker = self.frame.register(self.isInt)

        ### USER ENTERED PARAMETERS ###

        defaults = {
            'nt': 12,
            'niter': 50,
            'epL': 1e-9,
            'epT': 1e-9,
            'epV': 1e-7,
            'sigmaM': 4e-1,
            'sigmaR': 1e8,
            'sigmaP': 1,
            'a': 700,
            }
        
        self.param_vars = [tk.IntVar(value=defaults[key]) for key in defaults]
        labels = [ttk.Label(self.frame, text=key) for key in defaults]
        entries = [ttk.Entry(self.frame, textvariable=p,
                             validate='all',
                             validatecommand=(int_checker, '%P', '%W')) for p in self.param_vars]

        start_btn = ttk.Button(self.frame, text="Start", command=self.run) #start btn

        for row,label in enumerate(labels): label.grid(row=row, column=0)
        for row,entry in enumerate(entries): entry.grid(row=row, column=1, padx=10)
        start_btn.grid(row=len(defaults), columnspan=2)

    def isInt(self, P, W):
        if str.isdigit(P) or P == '': return True
        return False
    
    def run(self):
        print('hi!')
        # TODO: add call to stalign.LDDMM_3D here
        with open('Data\\Transforms_samples\\sample_1.pickle', 'rb') as file: #TODO: remove this blurb
            transform = pickle.load(file)
        self.transform = transform

        self.run_complete = True
    
    def next(self):
        if not self.run_complete:
            raise Exception('Cannot advance until run is complete')
        
        self.deactivate()
        return Boundary_Generator(self)

class Boundary_Generator(Page):

    def __init__(self, prev):

        super().__init__(prev.master)

        self.header = ''''''

        self.atlas = prev.atlas
        self.target = prev.target
        self.transform = prev.transform

        # read allen_ontology and store id to region name matches in namesdict
        ontology_name = 'Data\\allen_ontology.csv'
        O = pd.read_csv(ontology_name)

        self.namesdict = {}
        self.namesdict[0] = 'bg'
        for i,n in zip(O['id'],O['acronym']):
            self.namesdict[i] = n

        # get transformed annotation
        self.transform_atlas()

        self.region_list = np.delete(np.unique(self.region_graph), 0) # create list of regions found

        # create dictionary of all regions in region_graph , excluding 0 (bg) and pair it with a display state
        # 0 = off, 1 = on
        self.region_disp_dict = {} 

        self.get_boundaries() # get boundaries of each region

        # show target w regions overlayed and calibration point selection 
        self.create_figure(1,1)
        self.calibration_pts = []
        self.canvas.mpl_connect('button_press_event', self.onclick)
        self.canvas.mpl_connect('key_press_event',self.onpress)
        self.update()

        # list all regions in region_disp_dict with checkboxes to toggle
        self.region_picker_frame = tk.Frame(self.frame)
        self.create_region_picker()

        

        self.canvas.get_tk_widget().grid(row=0, column=0)
        self.toolbar_frame.grid(row=1, column=0)
        self.region_picker_frame.grid(row=0, column=1)
    
    def transform_atlas(self):
        A = self.transform['A']
        v = self.transform['v']
        xv = self.transform['xv']
        Xs = self.transform['Xs']

        vol = self.atlas.labels
        xL = self.atlas.pix_loc
        xJ = self.target.pix_loc
        print(f'xJ: {xJ}')

        # next chose points to sample on
        res = 10.0
        XJ = np.stack(np.meshgrid(np.zeros(1),xJ[0],xJ[1],indexing='ij'),-1)

        tform = STalign.build_transform3D(xv,v,A,direction='b',XJ=torch.tensor(XJ,device=A.device))

        AphiL = STalign.interp3D(
                xL,
                torch.tensor(vol[None].astype(np.float64),dtype=torch.float64,device=tform.device),
                tform.permute(-1,0,1,2),
                mode='nearest',)[0,0].cpu().int()

        self.region_graph = AphiL.numpy()
    
    def get_boundaries(self):
        self.boundaries = {}

        for region_id in self.region_list:
            region_name = self.namesdict[region_id]
            pts = np.fliplr(np.argwhere(self.region_graph==region_id)) # get all pts where region is marked
            
            cores,labels = dbscan(pts, eps=5, min_samples=1, metric='manhattan')

            for l in set(labels):
                if l == -1: continue
                cluster = pts[labels==l]

                hull = shapely.concave_hull(shapely.MultiPoint(cluster), 0.01) # get hull for cluster
                
                # only hulls defined as polygons can actually be cut out, other hulls will not be shown
                if hull.geom_type == 'Polygon':
                    new_region_name = f'{region_name}_{l}'
                    self.boundaries[new_region_name] = hull # add coordinates of hull to list
                    self.region_disp_dict[new_region_name] = tk.IntVar(value=1) # add it to the display dictionary

    def create_region_picker(self):
        checkbox_canvas = tk.Canvas(self.region_picker_frame, height=self.canvas.get_width_height()[1])
        
        # add scrollbar and configure
        scrollbar = ttk.Scrollbar(self.region_picker_frame, orient='vertical', 
                                  command=checkbox_canvas.yview)
        checkbox_canvas.config(yscrollcommand=scrollbar.set)
        
        # create scrollable frame for checkboxes within canvas
        checkbox_frame = tk.Frame(checkbox_canvas)
        checkbox_frame.bind(
            '<Configure>',
            lambda e: checkbox_canvas.config(scrollregion=checkbox_canvas.bbox("all"))
        )
        checkbox_canvas.create_window((0,0), anchor='nw', 
                                      window=checkbox_frame)
        
        # Add checkbuttons for regions
        for region in self.region_disp_dict.keys():
            btn = ttk.Checkbutton(checkbox_frame, text=region, 
                                  variable=self.region_disp_dict[region], 
                                  command=self.update)
            btn.pack(fill='x') # forces left-justify
        
        # resize canvas to match scroll frame width
        checkbox_frame.update()
        checkbox_canvas.config(width=checkbox_frame.winfo_width())

        # binding scrolling to application
        def MouseHandler(event):
            scroll = 0
            if event.num==5 or event.delta < 0:
                scroll = -1
            elif event.num==4 or event.delta > 0:
                scroll = 1
            if event.delta % 120 == 0: scroll *= -1 # windows is flipped
            checkbox_canvas.yview_scroll(scroll, 'units')

        checkbox_frame.bind_all('<MouseWheel>', MouseHandler )
        checkbox_frame.bind_all('<Button-4>', MouseHandler )
        checkbox_frame.bind_all('<Button-5>', MouseHandler )

        # Clear and Select All Buttons
        toggle_all_frame = ttk.Frame(self.region_picker_frame)
        clear_all_btn = ttk.Button(toggle_all_frame, text='Clear All', command=self.clear_all)
        select_all_btn = ttk.Button(toggle_all_frame, text='Select All', command=self.select_all)
        
        # Display everything
        clear_all_btn.pack(side='left')
        select_all_btn.pack(side='left')
        toggle_all_frame.pack(side='bottom')

        scrollbar.pack(side='right', fill='y')
        checkbox_canvas.pack(side='left', fill='both')

    def update(self):
        self.fig.axes[0].cla()
        self.fig.axes[0].imshow(self.target.get_img())
        #ski.transform.resize(np.pad(self.target.get_img(), ((234,),(394,))), [235.8032112, 330.80955089]))
        # TODO: ACTUALLY IMPLEMENT THE ADAPTIVE SIZING AND GET RID OF THIS ^^^
        print(self.region_graph.shape)
        print(self.target.get_img().shape)
        for region in self.region_disp_dict.items():
            bound = shapely.get_coordinates(self.boundaries[region[0]])

            if region[1].get() == 1:
                self.fig.axes[0].plot(bound[:,0], bound[:,1], 'r-', lw=.75)
        
        if len(self.calibration_pts):
            self.fig.axes[0].scatter(np.array(self.calibration_pts)[:,0], 
                                     np.array(self.calibration_pts)[:,1], 
                                     color='white', s=2)
        self.canvas.draw()
    
    def onclick(self, event):
        if event.xdata == None: return # clicked outside of axes
        ix, iy = int(event.xdata), int(event.ydata) # get x and y data of pt
        msg = 'calibration point'
        
        # update axis to clear out uncomitted pts
        self.update()

        if event.button == 1: # left click means add point at mouse location
            self.fig.axes[0].scatter([ix],[iy], color='red', s=2)
            self.new_pt = [ix, iy]
            msg = f'{msg} added at [x,y]=[{ix},{iy}]'
        elif event.button == 3: # right click means remove previously created point
            if self.new_pt == []: return
            msg = f'{msg} removed at [x,y]={self.new_pt}'
            self.new_pt = []
        
        print(msg)
        self.canvas.draw()

    def onpress(self, event):
        if event.key == 'enter': # enter key used to commit selected points to points list

            if not len(self.new_pt): # if missing a point, throw error
                print("ERROR: attempted calibration point with no point selected!")
                return

            # add new points to list, notify user, and clear out new points list
            self.calibration_pts.append(self.new_pt)
            print(f"Added {self.new_pt} to points list")
            self.new_pt = []
            self.update()
        
        if event.key == 'backspace': # backspace key used to remove recently committed point
            if len(self.calibration_pts) == 0: return # if no points to remove, simply return
            print(f'Removed {self.calibration_pts[-1]}') # user msg
            
            # remove last pair of poins
            self.calibration_pts.pop(-1)
            self.update() # refresh both axes

    def clear_all(self):
        for key in self.region_disp_dict.keys(): self.region_disp_dict[key].set(0)
        self.update()

    def select_all(self):
        for key in self.region_disp_dict.keys(): self.region_disp_dict[key].set(1)
        self.update()

    def next(self):
        filename = tk.filedialog.asksaveasfilename(defaultextension='xml', filetypes=[('xml files','.xml')])
        with open(filename, 'w') as file:
            self.write_to_xml(file)
        self.deactivate()

    def write_to_xml(self, f):

        f.write("<ImageData>\n")
        f.write("<GlobalCoordinates>1</GlobalCoordinates>\n")

        if len(self.calibration_pts) != 3: raise Exception("Error: three calibration points needed!")
        for i,pt in enumerate(self.calibration_pts):
            f.write(f"<X_CalibrationPoint_{i+1}>{pt[0]}</X_CalibrationPoint_{i+1}>\n")
            f.write(f"<Y_CalibrationPoint_{i+1}>{pt[1]}</Y_CalibrationPoint_{i+1}>\n")
        
        shapes = []
        for shape, disp in self.region_disp_dict.items():
            if disp.get() == 1: shapes.append(shape)

        f.write(f"<ShapeCount>{len(shapes)}</ShapeCount>\n")

        for i,shape in enumerate(shapes):
            f.write(f"<Shape_{i+1}>\n")
            self.write_shape_to_xml(shape,f)
            f.write(f"</Shape_{i+1}>\n")

        f.write("</ImageData>")
            
    def write_shape_to_xml(self, shape_name, f):
        points = shapely.get_coordinates(self.boundaries[shape_name])
        f.write(f"<PointCount>{len(points)+1}</PointCount>\n")

        for i in range(len(points)):
            f.write(f"<X_{i+1}>{points[i][0]}</X_{i+1}>\n")
            f.write(f"<Y_{i+1}>{points[i][1]}</Y_{i+1}>\n")  


    