import tkinter as tk
from tkinter import ttk
import os
from Images import *

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,  
NavigationToolbar2Tk) 

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
        self.atlas = Atlas(atlas_name)
        self.target = Target(target_address, self.atlas)
        
        # rotation scale
        self.rot_scale = ttk.Scale(self.frame, from_=60, to=-60, 
                                   orient='horizontal', length=200,
                                   variable=self.atlas.theta_degrees,
                                   command=self.update) 

        #slice scale
        self.slice_scale = ttk.Scale(self.frame, from_=0, to=self.atlas.img.shape[0]-1,
                                     orient='vertical', length=500, 
                                     variable=self.atlas.curr_slice,
                                     command=self.update)

        # showing images
        self.fig = Figure()
        self.canvas = FigureCanvasTkAgg(self.fig, self.frame)
        self.fig.subplots(1,2)
        self.fig.axes[1].imshow(self.target.get_img())
        self.update()
        
        # add mpl toolbar to allow zoom, translation
        toolbar_frame = ttk.Frame(self.frame)
        toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame) 
        toolbar.update()

        self.rot_scale.grid(row=0, column=1)
        self.slice_scale.grid(row=1, column=0)
        self.canvas.get_tk_widget().grid(row=1, column=1)
        toolbar_frame.grid(row=2, column=1)
    
    def update(self, _=None):
        self.fig.axes[0].imshow(self.atlas.get_img())
        self.canvas.draw()
    
    def next(self):
        self.deactivate()
        return Landmark_Annotator(self.master, self.atlas, self.target)
    
class Landmark_Annotator(Page):

    def __init__(self, master, atlas, target):
        super().__init__(master)

        self.atlas = atlas
        self.target = target
    
        self.imgs = [atlas.get_img(0), target.get_img()]
        self.extents = [atlas.get_extent(), target.get_extent()]
        self.points = [ [], [] ] # landmark points, points[0][i] in atlas corresponds with points[1][i] in target
        self.new_pt = [ [], [] ]
        self.pt_sz = 2
        
        # controls
        text = '''Mark atlas-target point pairs one pair at a time and submit each pair before marking the next! Click 'Next' to move on
        
        Controls:
        L-click\tmark point
        R-click\tremove point
        Enter\tsubmit point
        Backspace\tdelete last submitted'''
        instructions = ttk.Label(self.frame, text=text)

        # showing images
        self.fig = Figure()
        self.canvas = FigureCanvasTkAgg(self.fig, self.frame)
        self.fig.subplots(1,2)
        self.update()
        
        # add mpl toolbar to allow zoom, translation
        toolbar_frame = ttk.Frame(self.frame)
        toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame) 
        toolbar.update()

        instructions.grid(row=0, column=0)
        self.canvas.get_tk_widget().grid(row=1, column=0)
        toolbar_frame.grid(row=2, column=0)

        self.canvas.mpl_connect('button_press_event', self.onclick)
        self.canvas.mpl_connect('key_press_event',self.onpress)

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
            self.fig.axes[axis].scatter(np.array(self.points)[axis,:,2],
                                        np.array(self.points)[axis,:,1], 
                                        color='white', s=self.pt_sz)
        
        self.canvas.draw()
    
    def onclick(self, event):
        if event.xdata == None: return # clicked outside of axes
        ix, iy = int(event.xdata), int(event.ydata) # get x and y data of pt
        iz = 0
        msg = ''
        
        axis = -1
        # based on where user clicked, set axis and update output msg
        if event.inaxes == self.fig.axes[0]: # user clicked atlas
            axis = 0
            iz = self.atlas.pix_loc[0][self.atlas.curr_slice.get()] # z value corresponding to slice
            msg = "source at " + msg
        elif event.inaxes == self.fig.axes[1]: # user clicked target
            axis = 1
            msg = "target at " + msg
        else: print("ERROR: clicked outside axes")
        
        # update that axis to clear out uncomitted pts
        self.update(axis)

        if event.button == 1: # left click means add point at mouse location
            self.fig.axes[axis].scatter([ix],[iy], color='red', s=self.pt_sz)
            self.new_pt[axis] = [iz, iy, ix]
            msg = 'point added to ' + msg + f'[x,y]=[{ix},{iy}]'
        elif event.button == 3: # right click means remove previously created point
            msg = 'point removed from ' + msg + f'[x,y]={self.new_pt[axis][2:0:-1]}'
            self.new_pt[axis] = []
        
        print(msg)
        self.canvas.draw()

    def onpress(self, event):
        if event.key == 'enter': # enter key used to commit selected points to points list

            if not len(self.new_pt[0])*len(self.new_pt[1]): # if missing a point in either axis, throw error
                print("ERROR: attempted landmark save with one or more points missing!")
                return

            # add new points to list, notify user, and clear out new points list
            self.points[0].append(self.new_pt[0])
            self.points[1].append(self.new_pt[1])
            print(f"Added {self.new_pt[0][2:0:-1]} and {self.new_pt[1][2:0:-1]} to points list")
            self.new_pt[0] = []
            self.new_pt[1] = []
            self.update()
        
        if event.key == 'backspace': # backspace key used to remove recently committed point
            if len(self.points[0]) == 0: return # if no points to remove, simply return
            print(f'Removed [{self.points[0][-1][2:0:-1]}] and [{self.points[1][-1][2:0:-1]}]') # user msg
            
            # remove last pair of poins
            self.points[0].pop(-1)
            self.points[1].pop(-1)
            self.update() # refresh both axes



    