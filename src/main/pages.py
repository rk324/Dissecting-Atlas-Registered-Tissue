import tkinter as tk
from tkinter import ttk
import matplotlib as mpl
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,  
NavigationToolbar2Tk)
import os
import torch
import shapely
import pandas as pd
import numpy as np
from sklearn.cluster import dbscan

from images import *
from constants import *
from utils import *

from abc import ABC, abstractmethod

import pickle #TODO: remove if not using anymore

class Page(tk.Frame, ABC):

    def __init__(self, master, slides, atlases):
        super().__init__(master)
        self.slides = slides
        self.atlases = atlases
        self.header = ""
        self.create_widgets()

    @abstractmethod
    def create_widgets(self): pass

    @abstractmethod
    def show_widgets(self): pass

    # nested class for matplotlib figures in tkinter gui
    class TkFigure(Figure):

        def __init__(self, master, num_rows=1, num_cols=1, toolbar=False):
            super().__init__()
            self.canvas = FigureCanvasTkAgg(self, master)
            self.subplots(num_rows, num_cols)
        
            if toolbar:
                self.toolbar = NavigationToolbar2Tk(self.canvas, master)
                self.toolbar.update()
            
        def get_widget(self):
            return self.canvas.get_tk_widget()

        def update(self):
            self.canvas.draw_idle()
            self.canvas.flush_events()

    def activate(self):
        self.pack(expand=True, fill=tk.BOTH)
        self.show_widgets()
    
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

class Starter(Page):

    def __init__(self, master, slides, atlases):

        super().__init__(master, slides, atlases)
        self.header = 'Select samples and atlas'
    
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
    
    def done(self):
        # check that atlas picker and slides picker are not blank
        if self.atlas_name.get() == 'Choose Atlas': 
            raise Exception('Must select an atlas.')
        elif self.slides_folder_name.get() == '':
            raise Exception('Must select an folder containing sample images.')

        # load atlases
        atlas_folder_name = os.path.join('atlases', self.atlas_name.get())
        self.load_atlas_info(atlas_folder_name)

        # load slides
        if not os.path.exists(self.slides_folder_name.get()): 
            raise Exception ('Must select a folder containing sample images')
        self.load_slides(self.slides_folder_name.get())

        super().done()

    def load_atlas_info(self, path):
        for filename in os.listdir(path):
                curr_path = os.path.join(path, filename)
                if 'reference' in filename: 
                    ref_atlas_filename = curr_path
                elif 'label' in filename:
                    lab_atlas_filename = curr_path
                elif 'names_dict' in filename:
                    names_dict_filename = curr_path

        self.atlases[FSR].load_img(path=ref_atlas_filename)
        self.atlases[FSL].load_img(path=lab_atlas_filename)
        # load images for downscaled versiosn
        downscale_factor = 4
        self.atlases[DSR].load_img(
            img=self.atlases[FSR].img, 
            pix_dim=self.atlases[FSR].pix_dim, 
            ds_factor=downscale_factor
        )
        self.atlases[DSL].load_img(
            img=self.atlases[FSL].img, 
            pix_dim=self.atlases[FSL].pix_dim, 
            ds_factor=downscale_factor
        )
        self.atlases['names'] = pd.read_csv(names_dict_filename)

    def load_slides(self, path):
        for f in os.listdir(path):
            curr_path = os.path.join(path, f)
            if os.path.isfile(curr_path):
                new_slide = Slide(curr_path)
                self.slides.append(new_slide)

    def cancel(self):
        super().cancel()

class SlideProcessor(Page):

    def __init__(self, master, slides, atlases):
        super().__init__(master, slides, atlases)
        self.header = "Select slices and calibration points."
        self.currSlide = None

        self.newPointX = self.newPointY = -1
        self.newTargetX = self.newTargetY = -1
        self.newTargetData = None

        self.slice_selector = mpl.widgets.RectangleSelector(
            self.slide_viewer.axes[0], 
            self.on_select,
            button=1,
            useblit=True,
            interactive=True
        )

    def activate(self):
        super().activate()
        if self.annotation_mode.get() == 'point':
            self.activate_point_mode()
        elif self.annotation_mode.get() == 'rect':
            self.activate_rect_mode()

    def on_select(self, click, release):
        startX, startY = int(click.xdata), int(click.ydata)
        endX, endY = int(release.xdata), int(release.ydata)
        if startX==endX and startY==endY:
            self.newTargetX = -1
            self.newTargetY = -1
            self.newTargetData = None
        else:
            self.newTargetX = startX
            self.newTargetY = startY
            self.newTargetData = self.currSlide.get_img()[startY:endY, startX:endX]
        
        self.update_buttons()

    def on_click(self, event):
        if event.inaxes is None: return
        x,y = int(event.xdata), int(event.ydata)
        if event.button == 1:
            self.newPointX = x
            self.newPointY = y

        self.update_buttons()
        self.show_slide()

    def create_widgets(self): 
        # menu
        self.menu_frame = tk.Frame(self)
        self.annotation_mode = tk.StringVar(
            master=self.menu_frame,
            value="point"
        )
        self.point_radio = ttk.Radiobutton(
            master=self.menu_frame,
            command=self.activate_point_mode,
            value="point",
            variable=self.annotation_mode,
            text='Add Calibration Points',
            style='Toolbutton'
        )
        self.rectangle_radio = ttk.Radiobutton(
            master=self.menu_frame,
            command=self.activate_rect_mode,
            value="rect",
            variable=self.annotation_mode,
            text="Select Slices",
            style='Toolbutton'
        )
        
        self.menu_buttons_frame = tk.Frame(self.menu_frame)
        self.remove_btn = ttk.Button(
            master=self.menu_buttons_frame,
            text='',
            command = self.remove,
            state='disabled'
        )
        self.commit_btn = ttk.Button(
            master=self.menu_buttons_frame,
            text='',
            command=self.commit,
            state='disabled'
        )
        self.clear_btn = ttk.Button(
            master=self.menu_buttons_frame,
            text='Clear uncommitted',
            command=self.clear,
            state='disabled'
        )

        self.slide_nav_label = ttk.Label(self.menu_frame, text="Slide: ")
        self.curr_slide_var = tk.IntVar(master=self.menu_frame, value='1')
        self.slide_nav_combo = ttk.Combobox(
            master=self.menu_frame,
            values=[],
            state='readonly',
            textvariable=self.curr_slide_var,
        )
        self.slide_nav_combo.bind('<<ComboboxSelected>>', self.update)

        # slide viewer
        self.slides_frame = tk.Frame(self)
        self.slide_viewer = self.TkFigure(self.slides_frame, toolbar=True)
        self.slide_viewer.update()

        # paramater settings
        self.params_frame = tk.Frame(self)
        self.params_label = ttk.Label(
            self.params_frame,
            text="Adjust parameters for automatic alignment"
        )
        self.params_save_btn = ttk.Button(
            master=self.params_frame,
            text='Save parameters for slide',
            command=self.save_params
        )
        
        # basic parameter settings
        self.basic_frame = tk.Frame(self.params_frame, pady=10)
        self.basic_label = ttk.Label(
            master=self.basic_frame,
            text="Basic"
        )
        self.basic_param_label = ttk.Label(
            self.basic_frame, 
            text="Speed: "
        )
        self.basic_options = [
            'very slow 1-2 hrs/sample',
            'slow 15-30 min/sample', 
            'medium 3-5 min/sample', 
            'fast 20-30 sec/sample', 
            'skip automatic alignment' 
        ]
        self.basic_combo = ttk.Combobox(
            master=self.basic_frame,
            values = self.basic_options,
            state='readonly'
        )
        self.basic_combo.bind('<<ComboboxSelected>>', self.basic_to_advanced)
        self.basic_combo.set(self.basic_options[2])
        
        # advanced parameter settings
        self.advanced_frame = tk.Frame(self.params_frame)
        self.advanced_label = ttk.Label(
            master=self.advanced_frame,
            text="Advanced"
        )
        self.advanced_params_frame = tk.Frame(self.advanced_frame)
        self.param_vars, self.advanced_entries, self.advanced_param_labels = {}, {}, {}
        val_cmd = self.register(self.isFloat)
        for key, value in DEFAULT_STALIGN_PARAMS.items():
            self.param_vars[key] = tk.StringVar(master=self.advanced_params_frame, value=value)
            self.advanced_param_labels[key] = ttk.Label(master=self.advanced_params_frame, text=f'{key}:')
            self.advanced_entries[key] = ttk.Entry(
                master=self.advanced_params_frame, 
                textvariable=self.param_vars[key],
                validate='key',
                validatecommand=(val_cmd,'%P')
            )

    def show_widgets(self):
        
        self.update() # update buttons, slideviewer, stalign params

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # show menu
        self.menu_frame.grid(row=0, column=0, columnspan=2, sticky='nsew')
        self.point_radio.pack(side=tk.LEFT)
        self.rectangle_radio.pack(side=tk.LEFT)
        self.slide_nav_combo.config(
            values=[i+1 for i in range(len(self.slides))]
        )
        self.slide_nav_combo.pack(side=tk.RIGHT)
        self.slide_nav_label.pack(side=tk.RIGHT)

        self.menu_buttons_frame.pack()
        self.remove_btn.pack(side=tk.LEFT)
        self.commit_btn.pack(side=tk.LEFT)
        self.clear_btn.pack(side=tk.LEFT)

        # show slide viewer
        self.slides_frame.grid(row=1, column=0, sticky='nsew')
        self.slide_viewer.get_widget().pack(side=tk.LEFT, expand=True, fill=tk.BOTH)

        # show prameter settings
        self.params_frame.grid(row=1, column=1, sticky='nsew')
        self.params_label.pack()
        self.params_save_btn.pack(side=tk.BOTTOM, anchor='se')

        self.basic_frame.pack(fill=tk.X)
        self.basic_label.pack()
        self.basic_param_label.pack(side=tk.LEFT, anchor='nw')
        self.basic_combo.pack(side=tk.RIGHT, anchor='ne', expand=True, fill=tk.X)

        self.advanced_frame.pack(fill=tk.X)
        self.advanced_label.pack()
        self.advanced_params_frame.pack()
        self.advanced_params_frame.columnconfigure(1, weight=1)
        for i,key in enumerate(self.advanced_entries):
            label = self.advanced_param_labels[key]
            entry = self.advanced_entries[key]
            label.grid(row=i, column=0)
            entry.grid(row=i, column=1, sticky='ew')

    def show_slide(self, event=None):
        self.currSlide = self.slides[self.get_index()]
        self.slide_viewer.axes[0].cla()
        self.slide_viewer.axes[0].imshow(self.currSlide.get_img())
        
        for i,target in enumerate(self.currSlide.targets):
            edgecolor = COMMITTED_COLOR
            if i == self.currSlide.numTargets-1: edgecolor = REMOVABLE_COLOR
            self.slide_viewer.axes[0].add_patch(
                mpl.patches.Rectangle(
                    (target.x_offset, target.y_offset),
                    target.img_original.shape[1], 
                    target.img_original.shape[0],
                    edgecolor=edgecolor,
                    facecolor='none', 
                    lw=3
                )
            )
        
        point_size = 10
        if self.currSlide.numCalibrationPoints > 0:
            points = np.array(self.currSlide.calibration_points)
            self.slide_viewer.axes[0].scatter(
                points[:-1,0], 
                points[:-1,1], 
                color=COMMITTED_COLOR, 
                s=point_size
            )
            self.slide_viewer.axes[0].scatter(
                points[-1,0], 
                points[-1,1], 
                color=REMOVABLE_COLOR, 
                s=point_size
            )
        if not (self.newPointX == -1 and self.newPointY == -1):
            self.slide_viewer.axes[0].scatter(
                self.newPointX, self.newPointY, 
                color=NEW_COLOR, 
                s=point_size
            )

        self.slide_viewer.update()

    def update_buttons(self):
        mode = self.annotation_mode.get()
        if mode == 'rect':
            self.remove_btn.config(text="Remove Section")
            self.commit_btn.config(text="Add Section")
            canRemove = self.currSlide.numTargets > 0
            canAdd = self.newTargetData is not None
        elif mode == 'point':
            self.remove_btn.config(text="Remove Point")
            self.commit_btn.config(text="Add Point")
            canRemove = self.currSlide.numCalibrationPoints > 0
            canAdd = not self.newPointX==self.newPointY==-1
        else: return

        if canRemove:
            self.remove_btn.config(state='active')
        else:
            self.remove_btn.config(state='disabled')
        
        if canAdd:
            self.commit_btn.config(state='active')
            self.clear_btn.config(state='active')
        else:
            self.commit_btn.config(state='disabled')
            self.clear_btn.config(state='disabled')

    def update(self, event=None):
        self.currSlide = self.slides[self.get_index()]
        self.clear() # clear and show new slide image
        self.update_buttons() # update buttons

        curr_params = self.currSlide.stalign_params
        for key,var in self.param_vars.items():
            var.set(curr_params[key])
        
        self.set_basic()

    def save_params(self):
        curr_slide = self.currSlide
        for key, value in self.param_vars.items():
            curr_slide.set_param(key, float(value.get()))
        self.set_basic()
        # confirm
        print("parameters saved!")

    '''
    Set advanced settings based on basic settings
    '''
    def basic_to_advanced(self, event=None):
        # reset params to defaults
        for key, var in self.param_vars.items():
            var.set(DEFAULT_STALIGN_PARAMS[key])
        
        # set iterations based on speed setting
        speed = self.basic_combo.get()
        if "very slow" in speed:
            self.param_vars['iterations'].set('2000')
        elif "slow" in speed:
            self.param_vars['iterations'].set('500')
        elif "medium" in speed:
            self.param_vars['iterations'].set('100')
        elif "fast" in speed:
            self.param_vars['iterations'].set('10')
        else:
            self.param_vars['iterations'].set('0') #TODO: ensure STalign doesn't explod when given 0 iterations

    '''
    Set basic settings based on current slide's params
    '''
    def set_basic(self):
        num_iterations = float(self.param_vars['iterations'].get())
        
        for key, var in self.param_vars.items():
            if key == 'iterations': continue
            if float(var.get()) != DEFAULT_STALIGN_PARAMS[key]:
                self.basic_combo.set(f"Advanced settings estimated {1/24*num_iterations}")
                return
        
        if num_iterations == 2000: self.basic_combo.set(self.basic_options[0])
        elif num_iterations == 500: self.basic_combo.set(self.basic_options[1])
        elif num_iterations == 100: self.basic_combo.set(self.basic_options[2])
        elif num_iterations == 10: self.basic_combo.set(self.basic_options[3])
        elif num_iterations == 0: self.basic_combo.set(self.basic_options[4])
        else:
            self.basic_combo.set(f"Advanced settings estimated {2.5*num_iterations}") 

    def activate_point_mode(self):
        self.clear()
        self.slice_selector.set_active(False)
        self.click_event = self.slide_viewer.canvas.mpl_connect('button_press_event', self.on_click)
        self.update_buttons()

    def activate_rect_mode(self):
        self.clear()
        self.slice_selector.set_active(True)
        self.slide_viewer.canvas.mpl_disconnect(self.click_event)
        self.update_buttons()

    def remove(self):
        mode = self.annotation_mode.get()
        if mode == 'rect':
            self.remove_target()
        elif mode == 'point':
            self.remove_point()
        else: return

        self.show_slide()
        self.update_buttons

    def remove_target(self):
        self.currSlide.remove_target()

    def remove_point(self):
        self.currSlide.remove_calibration_point()

    def commit(self):
        mode = self.annotation_mode.get()
        if mode == 'rect':
            self.commit_target()
        elif mode == 'point':
            self.commit_point()
        else: return
        
        self.show_slide()
        self.update_buttons()

    def commit_target(self):
        if self.newTargetData is None: return
        self.currSlide.add_target(
            self.newTargetX, 
            self.newTargetY,
            self.newTargetData 
        )
        self.newTargetData = None
        self.newTargetX = self.newTargetY = -1
        self.slice_selector.clear()

    def commit_point(self):
        self.currSlide.add_calibration_point(
            [self.newPointX,self.newPointY]
        )
        self.newPointX = self.newPointY = -1

    def clear(self):
        self.newTargetX = self.newTargetY = -1
        self.newPointX = self.newPointY = -1
        self.newTargetData = None
        self.slice_selector.clear()
        self.show_slide()

    def isFloat(self, str):
        try:
            float(str)
            return True
        except ValueError:
            return False

    def get_index(self):
        return self.curr_slide_var.get()-1

    def done(self):
        # TODO: make the widget reposition to first slide w error and prompt user about error
        for i,slide in enumerate(self.slides):
            if slide.numTargets < 1: 
                raise Exception(f"No targets selected for slide #{i+1}")
            if slide.numCalibrationPoints != 3:
                raise Exception(f"You must select exactly three calibration points for each slide")
        super().done()

    def cancel(self):
        for slide in self.slides:
            slide.set_param() # reset params
            for i in range(slide.numCalibrationPoints):
                slide.remove_calibration_point() # remove calibration points
            for i in range(slide.numTargets):
                slide.remove_target() # remove targets
        super().cancel()

class TargetProcessor(Page):

    def __init__(self, master, slides, atlases):
        super().__init__(master, slides, atlases)
        self.header = "Select landmark points and adjust affine."
        self.currSlide = None
        self.currTarget = None
        self.new_points = [[],[]]
        self.point_size = 4

    def activate(self):
        if self.atlases[FSR].shape[0]*self.atlases[FSR].shape[1] > 1e9:
            self.preferred_atlas = "downscaled"
            atlas = self.atlases[DSR]
        else:
            self.preferred_atlas = "full size"
            atlas = self.atlases[FSR]

        for slide in self.slides:
            for target in slide.targets:
                self.update_img_estim(target)
                target.img_estim.set_pix_dim(atlas.pix_dim[1:]*ALPHA)
                target.img_estim.set_pix_loc()

        super().activate()

    def create_widgets(self):
        self.menu_frame = tk.Frame(self)
        self.slice_frame = tk.Frame(self)

        self.slide_nav_label = ttk.Label(self.menu_frame, text="Slide: ")
        self.curr_slide_var = tk.IntVar(master=self.menu_frame, value='1')
        self.slide_nav_combo = ttk.Combobox(
            master=self.menu_frame,
            values=[],
            state='readonly',
            textvariable=self.curr_slide_var,
        )
        self.slide_nav_combo.bind('<<ComboboxSelected>>', self.switch_slides)

        self.target_nav_label = ttk.Label(self.menu_frame, text="Target: ")
        self.curr_target_var = tk.IntVar(master=self.menu_frame, value='1')
        self.target_nav_combo = ttk.Combobox(
            master=self.menu_frame,
            values=[],
            state='readonly',
            textvariable=self.curr_target_var,
        )
        self.target_nav_combo.bind('<<ComboboxSelected>>', self.update)

        self.menu_buttons_frame = tk.Frame(self.menu_frame)
        self.remove_btn = ttk.Button(
            master=self.menu_buttons_frame,
            text='Remove Point',
            command = self.remove,
            state='disabled'
        )
        self.commit_btn = ttk.Button(
            master=self.menu_buttons_frame,
            text='Add Point',
            command=self.commit,
            state='disabled'
        )
        self.clear_btn = ttk.Button(
            master=self.menu_buttons_frame,
            text='Clear uncommitted',
            command=self.clear,
            state='disabled'
        )

        self.slice_viewer = self.TkFigure(self.slice_frame, num_cols=2, toolbar=False)
        self.click_event = self.slice_viewer.canvas.mpl_connect('button_press_event', self.on_click)

        self.rotation_frame = tk.Frame(self.slice_frame)
        self.thetas = [tk.IntVar(self.rotation_frame, value=0) for i in range(3)]
        self.x_rotation_scale = ttk.Scale(
            master=self.rotation_frame, 
            from_=90, to=-90, 
            orient='vertical', 
            variable=self.thetas[2],
            command=self.show_atlas
        )
        self.y_rotation_scale = ttk.Scale(
            master=self.rotation_frame, 
            from_=90, to=-90, 
            orient='vertical', 
            variable=self.thetas[1],
            command=self.show_atlas
        )
        self.z_rotation_scale = ttk.Scale(
            master=self.rotation_frame, 
            from_=180, to=-180, 
            orient='vertical', 
            variable=self.thetas[0],
            command=self.show_atlas
        )
        self.rotation_labels = [ttk.Label(
                                    master=self.rotation_frame,
                                    text=self.thetas[i].get()
                                ) for i in range(3)]

        self.translation_frame = tk.Frame(self.slice_frame)
        self.translation = tk.DoubleVar(self.translation_frame, value=0)
        self.translation_scale = ttk.Scale(
            master=self.translation_frame,
            from_=self.atlases[DSR].pix_loc[0][0],
            to_=self.atlases[DSR].pix_loc[0][-1],
            orient='horizontal',
            variable=self.translation,
            command=self.show_atlas
        )
        self.translation_label = ttk.Label(
            master=self.translation_frame,
            text=self.translation.get()
        )

    def show_widgets(self):
        
        self.update()

        self.menu_frame.pack(fill=tk.X)
        self.slice_frame.pack(expand=True, fill=tk.BOTH)
        self.slice_frame.grid_rowconfigure(0, weight=1)
        self.slice_frame.grid_columnconfigure(0, weight=1)
        self.slice_frame.grid_columnconfigure(1, weight=1)

        self.slide_nav_label.pack(side=tk.LEFT)
        self.slide_nav_combo.pack(side=tk.LEFT)
        
        self.target_nav_combo.pack(side=tk.RIGHT)
        self.target_nav_label.pack(side=tk.RIGHT)

        self.menu_buttons_frame.pack()
        self.remove_btn.pack(side=tk.LEFT)
        self.commit_btn.pack(side=tk.LEFT)
        self.clear_btn.pack(side=tk.LEFT)

        self.slice_viewer.get_widget().grid(
            row=0, 
            column=0, 
            columnspan=2, 
            sticky='nsew'
        )
        
        self.rotation_frame.grid(row=0, column=2, sticky='nsew')
        self.rotation_frame.grid_rowconfigure(0, weight=1)
        self.x_rotation_scale.grid(row=0, column=0, sticky='nsew')
        self.y_rotation_scale.grid(row=0, column=1, sticky='nsew')
        self.z_rotation_scale.grid(row=0, column=2, sticky='nsew')
        self.rotation_labels[2].grid(row=1, column=0)
        self.rotation_labels[1].grid(row=1, column=1)
        self.rotation_labels[0].grid(row=1, column=2)
        
        self.translation_frame.grid(row=1,column=1, sticky='nsew')
        self.translation_scale.pack(fill=tk.X)
        self.translation_label.pack()

    def update(self, event=None):
        self.currSlide = self.slides[self.get_slide_index()]
        self.slide_nav_combo.config(
            values=[i+1 for i in range(len(self.slides))]
        )

        self.currTarget = self.currSlide.targets[self.get_target_index()]
        self.target_nav_combo.config(
            values=[i+1 for i in range(self.currSlide.numTargets)]
        )

        if (self.currTarget.thetas == np.array([0,0,0])).all():
            n = 0
            thetas_avg = np.array([0,0,0])
            for target in self.currSlide.targets:
                if (target.thetas != np.array([0,0,0])).any():
                    thetas_avg += target.thetas
                    n += 1
            if n > 0: self.currTarget.thetas = np.divide(thetas_avg,n).astype('int64')

        for i in range(3): self.thetas[i].set(self.currTarget.thetas[i])
        self.translation.set(self.currTarget.T_estim[0])

        self.new_points = [[],[]] # reset new points

        self.show_target()
        self.show_atlas()
        self.update_buttons()

    def switch_slides(self, event=None):
        self.curr_target_var.set(1)
        self.update()

    def show_target(self):
        # show target image, show landmark points
        self.slice_viewer.axes[0].cla()
        self.slice_viewer.axes[0].set_axis_off()
        self.slice_viewer.axes[0].set_title(f"Slide #{self.get_slide_index()+1}\nSlice #{self.get_target_index()+1}")
        self.slice_viewer.axes[0].imshow(self.currTarget.img, cmap='Greys')
        
        point = self.new_points[0]
        if len(point) == 2: 
            self.slice_viewer.axes[0].scatter(
                point[1], point[0], 
                color=NEW_COLOR,
                s=self.point_size
            )

        landmarks = np.array(self.currTarget.landmarks['target'])
        if len(landmarks) > 0:
            self.slice_viewer.axes[0].scatter(
                landmarks[:-1, 1], landmarks[:-1, 0],
                color=COMMITTED_COLOR,
                s=self.point_size
            )
            self.slice_viewer.axes[0].scatter(
                landmarks[-1, 1], landmarks[-1, 0],
                color=REMOVABLE_COLOR,
                s=self.point_size
            )

        self.slice_viewer.update()

    def update_img_estim(self, target):

        if self.preferred_atlas == "downscaled":
            atlas = self.atlases[DSR]
        else:
            atlas = self.atlases[FSR]

        xE = [ALPHA*x for x in atlas.pix_loc]
        XE = np.stack(np.meshgrid(np.zeros(1),xE[1],xE[2],indexing='ij'),-1)
        L,T = target.get_LT()
        slice_transformed = (L @ XE[...,None])[...,0] + T
        slice_img = atlas.get_img(slice_transformed)
        
        target.img_estim.load_img(slice_img)

    def show_atlas(self, event=None):
        self.slice_viewer.axes[1].cla()
        self.slice_viewer.axes[1].set_title("Atlas")
        self.slice_viewer.axes[1].set_axis_off()

        for i in range(3): 
            self.currTarget.thetas[i] = self.thetas[i].get()
            self.rotation_labels[i].config(text=self.thetas[i].get())

        self.currTarget.T_estim[0] = self.translation.get()
        self.translation_label.config(text=self.translation.get())

        self.update_img_estim(self.currTarget)
        self.slice_viewer.axes[1].imshow(self.currTarget.img_estim.get_img(), cmap='Grays')

        point = self.new_points[1]
        if len(point) == 2: 
            self.slice_viewer.axes[1].scatter(
                point[1], point[0], 
                color='red',
                s=self.point_size
            )

        landmarks = np.array(self.currTarget.landmarks['atlas'])
        if len(landmarks) > 0:
            self.slice_viewer.axes[1].scatter(
                landmarks[:-1, 1], landmarks[:-1, 0],
                color=COMMITTED_COLOR,
                s=self.point_size
            )
            self.slice_viewer.axes[1].scatter(
                landmarks[-1, 1], landmarks[-1, 0],
                color=REMOVABLE_COLOR,
                s=self.point_size
            )
        
        self.slice_viewer.update()

    def update_buttons(self):

        canRemove = self.currTarget.num_landmarks > 0
        canAdd = len(self.new_points[0]) == 2 and len(self.new_points[1]) == 2
        canClear = len(self.new_points[0]) == 2 or len(self.new_points[1]) == 2

        if canRemove:
            self.remove_btn.config(state='active')
        else:
            self.remove_btn.config(state='disabled')
        
        if canAdd:
            self.commit_btn.config(state='active')
        else:
            self.commit_btn.config(state='disabled')
        
        if canClear:
            self.clear_btn.config(state='active')
        else:
            self.clear_btn.config(state='disabled')

    def on_click(self, event):
        if event.inaxes is None: return

        new_x, new_y = int(event.xdata), int(event.ydata)
        if event.inaxes is self.slice_viewer.axes[0]:
            # clicked on target
            self.new_points[0] = [new_y, new_x]
            self.show_target()
        elif event.inaxes is self.slice_viewer.axes[1]:
            # clicked on atlas
            self.new_points[1] = [new_y, new_x]
            self.show_atlas()
        
        self.update_buttons()

    def remove(self):
        self.currTarget.remove_landmarks()
        self.update()

    def commit(self):
        self.currTarget.add_landmarks(self.new_points[0], self.new_points[1])
        self.new_points = [[],[]]
        self.update()

    def clear(self):
        self.new_points = [[],[]]
        self.update()

    def done(self):
        # estimate pixel dimensions
        for slide in self.slides:
            slide.estimate_pix_dim()
        super().done()

    def cancel(self):
        # clear affine estimation and landmark points
        for slide in self.slides:
            for target in slide.targets:
                target.thetas = np.array([0, 0, 0])
                target.T_estim = np.array([0, 0, 0])
                for i in range(target.num_landmarks): target.remove_landmarks()
        super().cancel()
    
    def get_slide_index(self):
        return self.curr_slide_var.get()-1
    
    def get_target_index(self):
        return self.curr_target_var.get()-1

class STalignRunner(Page):

    def __init__(self, master, slides, atlases):
        super().__init__(master, slides, atlases)
        self.header = "Running STalign."
    
    def activate(self):
        self.estimate_time()
        if self.atlases[FSR].shape[0]*self.atlases[FSR].shape[1] > 1e9:
            self.preferred_atlas = "downscaled"
        else:
            self.preferred_atlas = "full size"

        super().activate()

    def estimate_time(self):
        totalIterations = 0
        for slide in self.slides:
            numIt = slide.stalign_params['iterations']
            numTargets = slide.numTargets
            totalIterations += numIt * numTargets
        self.progress_bar.config(maximum=totalIterations)

        time_sec = 3*totalIterations # ~3 sec/iteration
        time_str = STalignRunner.seconds_to_string(time_sec)

        label_txt = f'Estimated Duration: {time_str}' #TODO
        self.info_label.config(text=label_txt)

    # converts number of seconds to a human readable string
    def seconds_to_string(s):
        units = {
            "day":24*60*60,
            "hour":60*60,
            "minute":60,
            "second":1
        }
        output_dict = {
            "day":0,
            "hour":0,
            "minute":0,
            "second":0
        }

        for unit,duration in units.items():
            output_dict[unit] = int(s//duration)
            s = s % duration
        
        output = [f'{value} {unit}(s)' for unit,value in output_dict.items() if value != 0]
        return " ".join(output)

    def create_widgets(self):
        self.info_label = ttk.Label(
            master=self,
        )

        self.start_btn = ttk.Button(
            master=self,
            command=self.run,
            text='Run'
        )

        self.progress_bar = ttk.Progressbar(
            master=self,
            mode='determinate',
            orient='horizontal',
            value=0
        )

    def show_widgets(self):
        self.info_label.pack()
        self.start_btn.pack()

    def run(self):
        print('running!')
        self.start_btn.pack_forget()
        self.progress_bar.pack()
        # specify device
        if torch.cuda.is_available():
            device = 'cuda'
        else:
            device = 'cpu'
        
        for sn,slide in enumerate(self.slides):
            for tn,target in enumerate(slide.targets):
                label_txt = f'Running STalign on Target #{tn+1} of Slide #{sn+1}'
                print(label_txt)
                self.info_label.config(text=label_txt)
                self.update()

                # processing points
                points_target_pix = np.array(target.landmarks['target'])
                points_atlas_pix = np.array(target.landmarks['atlas'])
                
                if self.preferred_atlas == 'downscaled':
                    atlas = self.atlases[DSR]
                else: atlas = self.atlases[FSR]
                xE = [ALPHA*x for x in atlas.pix_loc]
                XE = np.stack(np.meshgrid(np.zeros(1),xE[1],xE[2],indexing='ij'),-1)
                L,T = target.get_LT()
                slice_pts = (L @ XE[...,None])[...,0] + T

                points_atlas = slice_pts[0, points_atlas_pix[:,0], points_atlas_pix[:,1]]
                points_target = points_target_pix * target.pix_dim + [target.pix_loc[0][0], target.pix_loc[1][0]]
                points_target = np.insert(points_target, 0, 0, axis=1)

                # processing input affine
                L = np.linalg.inv(L)
                T = -T

                # final target and atlas processing
                xI = self.atlases[FSR].pix_loc
                I = self.atlases[FSR].img
                I = I[None] / np.mean(np.abs(I), keepdims=True)
                I = np.concatenate((I, (I-np.mean(I))**2))
                xJ = target.pix_loc
                J = target.img
                J = J[None] / np.mean(np.abs(J))

                target.transform = LDDMM_3D_LBGFS(
                    xI,I,xJ,J,
                    T=T,L=L,
                    device=device,
                    pointsI=points_atlas, # DO NOT CHANGE
                    pointsJ=points_target, # DO NOT CHANGE
                    nt=int(slide.stalign_params['timesteps']),
                    niter=int(slide.stalign_params['iterations']),
                    sigmaM = slide.stalign_params['sigmaM'],
                    sigmaP = slide.stalign_params['sigmaP'],
                    sigmaR = slide.stalign_params['sigmaR'],
                    a = slide.stalign_params['resolution'],
                    progress_bar=self.progress_bar
                )

        self.info_label.config(text="Done!")
        self.progress_bar.pack_forget()
        self.update()
    
    def done(self):
        super().done()
    
    def cancel(self):
        super().cancel()

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


    