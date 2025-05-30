import tkinter as tk
from tkinter import ttk
import ttkwidgets
import matplotlib as mpl
import os
import torch
import shapely
import pandas as pd
import numpy as np
from sklearn.cluster import dbscan
import shutil
import glob

from images import *
from constants import *
from utils import *

from abc import ABC, abstractmethod

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
        self.atlases[FSL].load_img(path=lab_atlas_filename, normalize=False)
        # load images for downscaled version
        pix_dim_full = self.atlases[FSR].pix_dim

        downscale_factor = tuple([int(max(1, 50/dim)) for dim in pix_dim_full])
        self.atlases[DSR].load_img(
            img=self.atlases[FSR].img, 
            pix_dim=self.atlases[FSR].pix_dim, 
            ds_factor=downscale_factor
        )
        self.atlases[DSL].load_img(
            img=self.atlases[FSL].img, 
            pix_dim=self.atlases[FSL].pix_dim, 
            ds_factor=downscale_factor,
            normalize=False
        )
        self.atlases['names'] = pd.read_csv(names_dict_filename, index_col='name')
        self.atlases['names'].loc['empty','id'] = 0

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
        self.slide_viewer = TkFigure(self.slides_frame, toolbar=True)
        self.slide_viewer.update()

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
        self.slides.clear()
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
        atlas = self.atlases[DSR]
        for slide in self.slides:
            for target in slide.targets:
                self.update_img_estim(target)
                target.img_estim.set_pix_dim(atlas.pix_dim[1:]*ALPHA)
                target.img_estim.set_pix_loc()

        self.translation_scale.config(
            from_=self.atlases[DSR].pix_loc[0][0],
            to_=self.atlases[DSR].pix_loc[0][-1]
        )

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

        self.figure_frame = tk.Frame(self.slice_frame)
        self.slice_viewer = TkFigure(self.figure_frame, num_cols=2, toolbar=True)
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
            orient='horizontal',
            variable=self.translation,
            command=self.show_atlas
        )
        self.translation_label = ttk.Label(
            master=self.translation_frame,
            text=self.translation.get()
        )

        # paramater settings
        self.params_frame = tk.Frame(self)
        self.params_label = ttk.Label(
            self.params_frame,
            text="Adjust parameters for automatic alignment"
        )
        self.params_save_btn = ttk.Button(
            master=self.params_frame,
            text='Save parameters for slice',
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
        
        self.update()
        
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.menu_frame.grid(row=0, column=0, columnspan=2, sticky='nsew')
        self.slice_frame.grid(row=1, column=0, sticky='nsew')
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

        self.figure_frame.grid(
            row=0, 
            column=0, 
            columnspan=2, 
            sticky='nsew'
        )
        self.slice_viewer.get_widget().pack(expand=True, fill=tk.BOTH)
        
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

        curr_params = self.currTarget.stalign_params
        for key,var in self.param_vars.items():
            var.set(curr_params[key])
        
        self.set_basic()

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

        atlas = self.atlases[DSR]
        
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
        #TODO: make save parameters button only active if changes to save
        #TODO: add options to save stalign params to slice, slide, or all

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
    
    def save_params(self):
        for key, value in self.param_vars.items():
            self.currTarget.set_param(key, float(value.get()))
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
            self.param_vars['iterations'].set('1') #TODO: ensure STalign doesn't explod when given 0 iterations

    '''
    Set basic settings based on current targets's params
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
        elif num_iterations == 1: self.basic_combo.set(self.basic_options[4])
        else:
            self.basic_combo.set(f"Advanced settings estimated {2.5*num_iterations}") 

    def done(self):
        # estimate pixel dimensions
        for slide in self.slides:
            slide.estimate_pix_dim()
        super().done()

    def cancel(self):
        # clear affine estimation and landmark points
        for slide in self.slides:
            for target in slide.targets:
                target.set_param() # reset params
                target.thetas = np.array([0, 0, 0])
                target.T_estim = np.array([0, 0, 0])
                for i in range(target.num_landmarks): target.remove_landmarks()
        super().cancel()
    
    def isFloat(self, str):
        try:
            float(str)
            return True
        except ValueError:
            return False

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
        super().activate()

    def estimate_time(self):
        totalIterations = 0
        for slide in self.slides:
            for target in slide.targets:
                numIt = target.stalign_params['iterations']
                totalIterations += numIt
        self.progress_bar.config(maximum=totalIterations)

        time_sec = 3*totalIterations # ~3 sec/iteration
        time_str = STalignRunner.seconds_to_string(time_sec)

        label_txt = f'Estimated Duration: {time_str}'
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

        self.results_viewer = tk.Frame(self)
        self.create_result_viewer()

    def show_widgets(self):
        self.info_label.pack()
        self.start_btn.pack()
        self.show_result_viewer()
        
    def process_points(self, target):
        if target.num_landmarks > 0:
            points_target_pix = np.array(target.landmarks['target'])
            points_atlas_pix = np.array(target.landmarks['atlas'])
            
            atlas = self.atlases[DSR]
            xE = [ALPHA*x for x in atlas.pix_loc]
            XE = np.stack(np.meshgrid(np.zeros(1),xE[1],xE[2],indexing='ij'),-1)
            L,T = target.get_LT()
            slice_pts = (L @ XE[...,None])[...,0] + T

            points_atlas = slice_pts[0, points_atlas_pix[:,0], points_atlas_pix[:,1]]
            points_target = points_target_pix * target.pix_dim + [target.pix_loc[0][0], target.pix_loc[1][0]]
            points_target = np.insert(points_target, 0, 0, axis=1)
            return {"target": points_target, "atlas": points_atlas}
        else:
            return {"target": None, "atlas": None}  

    def get_transform(self, target, device):
        # processing points
        processed_points = self.process_points(target)

        # processing input affine
        L,T = target.get_LT()
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

        transform = LDDMM_3D_LBGFS(
            xI,I,xJ,J,
            T=T,L=L,
            device=device,
            pointsI=processed_points["atlas"], # DO NOT CHANGE
            pointsJ=processed_points["target"], # DO NOT CHANGE
            nt=int(target.stalign_params['timesteps']),
            niter=int(target.stalign_params['iterations']),
            sigmaM = target.stalign_params['sigmaM'],
            sigmaP = target.stalign_params['sigmaP'],
            sigmaR = target.stalign_params['sigmaR'],
            a = target.stalign_params['resolution'],
            progress_bar=self.progress_bar
        )
        return transform

    def get_segmentation(self, target):
        transform = target.transform
        At = transform['A']
        v = transform['v']
        xv = transform['xv']

        atlas = self.atlases[FSL]
        vol = atlas.img
        dxL = atlas.pix_dim
        nL = atlas.shape
        xL = [np.arange(n)*d - (n-1)*d/2 for n,d in zip(nL,dxL)]

        # next chose points to sample on
        XJ = np.stack(np.meshgrid(
            np.zeros(1),
            target.pix_loc[0],
            target.pix_loc[1],
            indexing='ij'),-1)

        tform = STalign.build_transform3D(
            xv,v,At,
            direction='b',
            XJ=torch.tensor(XJ,device=At.device)
        )

        AphiL = STalign.interp3D(
            xL,
            torch.tensor(vol[None].astype(np.float64),dtype=torch.float64,device=tform.device),
            tform.permute(-1,0,1,2),
            mode='nearest'
        )[0,0].cpu().int()
        
        return AphiL.numpy()

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
                label_txt = f'Running STalign on Slice #{tn+1} of Slide #{sn+1}'
                print(label_txt)
                self.info_label.config(text=label_txt)
                self.update()

                target.transform = self.get_transform(target, device)
                target.seg_stalign = self.get_segmentation(target)

        self.info_label.config(text="Done!")
        self.progress_bar.pack_forget()
        self.show_results()
        self.update()

    def create_result_viewer(self):
        # for showing results after running stalign
        self.menu_frame = tk.Frame(self.results_viewer)
        self.slice_frame = tk.Frame(self.results_viewer)

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
        self.target_nav_combo.bind('<<ComboboxSelected>>', self.update_result_viewer)

        self.slice_viewer = TkFigure(self.slice_frame, toolbar=True)

    def show_result_viewer(self):
        self.results_viewer.grid_rowconfigure(1, weight=1)
        self.results_viewer.grid_columnconfigure(0, weight=1)
        self.menu_frame.grid(row=0, column=0, sticky='nsew')
        self.slice_frame.grid(row=1, column=0, sticky='nsew')

        self.slide_nav_label.pack(side=tk.LEFT)
        self.slide_nav_combo.pack(side=tk.LEFT)
        
        self.target_nav_combo.pack(side=tk.RIGHT)
        self.target_nav_label.pack(side=tk.RIGHT)

        self.slice_viewer.get_widget().pack(expand=True, fill=tk.BOTH)

    def switch_slides(self, event=None):
        self.curr_target_var.set(1)
        self.update_result_viewer()
    
    def update_result_viewer(self, event=None):
        self.currSlide = self.slides[self.get_slide_index()]
        self.currTarget = self.currSlide.targets[self.get_target_index()]
        self.target_nav_combo.config(
            values=[i+1 for i in range(self.currSlide.numTargets)]
        )
        self.show_seg()

    def show_seg(self):
        self.slice_viewer.axes[0].cla()
        seg_img = self.currTarget.get_img(seg="stalign")
        self.slice_viewer.axes[0].imshow(seg_img)
        self.slice_viewer.update()

    def show_results(self):
        self.currSlide = None
        self.currTarget = None
        self.update_result_viewer()

        self.slide_nav_combo.config(
            values=[i+1 for i in range(len(self.slides))]
        )
        self.results_viewer.pack(expand=True, fill=tk.BOTH)
    
    def get_slide_index(self):
        return self.curr_slide_var.get()-1
    
    def get_target_index(self):
        return self.curr_target_var.get()-1

    def done(self):
        super().done()
    
    def cancel(self):
        self.results_viewer.pack_forget()
        for slide in self.slides:
            for target in slide.targets:
                target.transform = None
                target.seg_stalign = None
        super().cancel()

class VisuAlignRunner(Page):

    def __init__(self, master, slides, atlases):
        super().__init__(master, slides, atlases)
        self.header = "Running VisuAlign."

    def activate(self):
        # stack seg_stalign of all targets and pad as necessary to create 3 dimensions np.array
        raw_stack = [target.seg_stalign for slide in self.slides for target in slide.targets]
        shapes = np.array([seg.shape for seg in raw_stack])
        max_dims = [shapes[:,0].max(), shapes[:,1].max()]
        paddings = max_dims-shapes
        stack = np.array([np.pad(r, ((p[0],0),(0,p[1]))) for p,r in zip(paddings, raw_stack)])
        stack = np.transpose(np.flip(stack, axis=(0,1)), (-1,0,1))
        nifti = nib.Nifti1Image(stack, np.eye(4)) # create nifti obj
        nib.save(nifti, os.path.join("VisuAlign-v0_9//custom_atlas.cutlas//labels.nii.gz"))

        visualign_export_folder = 'EXPORT_VISUALIGN_HERE'
        if not os.path.exists(visualign_export_folder):
            os.mkdir(visualign_export_folder)

        with open('CLICK_ME.json','w') as f:
            f.write('{')
            f.write('"name":"", ')
            f.write('"target":"custom_atlas.cutlas", ')
            f.write('"aligner": "prerelease_1.0.0", ')
            f.write('"slices": [')
            i=0
            for sn,slide in enumerate(self.slides):
                for ti,t in enumerate(slide.targets): 
                    ski.io.imsave(f'DELETE_ME_{sn}_{ti}.jpg',t.img_original)
                    f.write('{')
                    h = raw_stack[i].shape[0]
                    w = raw_stack[i].shape[1]
                    f.write(f'"filename": "DELETE_ME_{sn}_{ti}.jpg", ')
                    f.write(f'"anchoring": [0, {len(raw_stack)-i-1}, {h}, {w}, 0, 0, 0, 0, -{h}], ')
                    f.write(f'"height": {h}, "width": {w}, ')
                    f.write('"nr": 1, "markers": []}')
                    if i < len(raw_stack)-1: f.write(',')
                    i += 1
            f.write(']}')
        
        super().activate()

    def deactivate(self):
        os.remove('CLICK_ME.json')
        os.remove('VisuAlign-v0_9/custom_atlas.cutlas/labels.nii.gz')
        shutil.rmtree("EXPORT_VISUALIGN_HERE")
        for f in glob.glob('*DELETE_ME*'): os.remove(f)
        super().deactivate()

    def create_widgets(self):
        self.run_btn = ttk.Button(
            master=self,
            text="Open VisuAlign",
            command=self.run
        )

        self.instructions_label = ttk.Label(
            master=self,
            text="Instructions:\n1. Click \"Open VisuAlign\" button\n2. Click File > Open > \"CLICK_ME.json\"\n3. Adjust alignment with VisuAlign until satisfied\n4. Click File > Export > \"EXPORT_VISUALIGN_HERE\"\n5. Close VisuAlign after notification of successful saving of segmentation"
        )

    def show_widgets(self):
        self.instructions_label.pack()
        self.run_btn.pack()

    def run(self):
        print("running visualign")
        cmd = rf"cd VisuAlign-v0_9 && {os.path.join("bin","java.exe")} --module qnonlin/visualign.QNonLin"
        os.system(cmd)
        
    def done(self):
        #TODO: handle if visualign adjustment not used (no exported files)
        regions_nutil = pd.read_json(r'resources/Rainbow 2017.json')
        for sn,slide in enumerate(self.slides):
            for ti,t in enumerate(slide.targets):
                visualign_nl_flat_filename = f'EXPORT_VISUALIGN_HERE//DELETE_ME_{sn}_{ti}_nl.flat'
                with open(visualign_nl_flat_filename, 'rb') as fp:
                    buffer = fp.read()
                shape = np.frombuffer(buffer, dtype=np.dtype('>i4'), offset=1, count=2) 
                data = np.frombuffer(buffer, dtype=np.dtype('>i2'), offset=9)
                data = data.reshape(shape[::-1])
                data = data[:-1,:-1]
                
                seg_visualign_names = regions_nutil['name'].to_numpy()[data] 
                seg_visualign = seg_visualign_names.copy()
                for region_name in np.unique(seg_visualign_names):
                    mask = seg_visualign_names==region_name
                    seg_visualign[mask] = self.atlases['names'].id[region_name]
                    
                t.seg_visualign = seg_visualign.astype(int)
        super().done()
    
    def cancel(self):
        super().cancel()

class RegionPicker(Page):

    def __init__(self, master, slides, atlases):
        super().__init__(master, slides, atlases)
        self.header = "Selecting ROIs"
        self.currSlide = None
        self.currTarget = None
        self.rois = []
        self.region_colors = ['red','yellow','green','orange','brown','white','black','grey','cyan','pink','tan']
    
    def activate(self):
        self.slide_nav_combo.config(
            values=[i+1 for i in range(len(self.slides))]
        )
        self.make_tree()

        super().activate()

    def make_tree(self):
        regions = self.atlases['names']
        for name,row in regions.iterrows():
            id = row['id']
            parent = row['parent_structure_id']
            if pd.isna(parent): parent = ""
            self.region_tree.insert(
                parent=parent,
                index="end",
                iid=id,
                text=name
            )
        self.region_tree.expand_all()

    def create_widgets(self):
        self.menu_frame = tk.Frame(self)
        self.slice_frame = tk.Frame(self)
        self.region_frame = tk.Frame(self)

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

        self.slice_viewer = TkFigure(self.slice_frame, toolbar=True)
        self.slice_viewer.canvas.mpl_connect('motion_notify_event', self.on_move)
        self.slice_viewer.canvas.mpl_connect('button_press_event', self.on_click)

        self.region_tree = self.ModifiedCheckboxTreeView(
            master=self.region_frame
        )

        self.region_tree.bind('<Motion>',self.check_update)
        self.region_tree.bind('<ButtonRelease-1>',self.check_update)

    def show_widgets(self):
        self.update()
        
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=5)
        self.grid_columnconfigure(1, weight=1)

        self.menu_frame.grid(row=0, column=0, sticky='nsew')
        self.slice_frame.grid(row=1, column=0, sticky='nsew')
        self.region_frame.grid(row=0, rowspan=2, column=1, sticky='nsew')

        self.slide_nav_label.pack(side=tk.LEFT)
        self.slide_nav_combo.pack(side=tk.LEFT)
        
        self.target_nav_combo.pack(side=tk.RIGHT)
        self.target_nav_label.pack(side=tk.RIGHT)

        self.slice_viewer.get_widget().pack(expand=True, fill=tk.BOTH)

        self.region_tree.pack(expand=True, fill=tk.BOTH)
        #TODO: figure out how to make entire tree horizontal visible

    def switch_slides(self, event=None):
        self.curr_target_var.set(1)
        self.update()

    def check_update(self, event=None):
        new_rois = [int(float(s)) for s in self.region_tree.get_checked()]
        if self.rois != new_rois:
            self.rois = new_rois
            self.show_seg()

    def update(self, event=None):
        self.currSlide = self.slides[self.get_slide_index()]
        self.currTarget = self.currSlide.targets[self.get_target_index()]
        self.target_nav_combo.config(
            values=[i+1 for i in range(self.currSlide.numTargets)]
        )
        self.rois = [int(float(s)) for s in self.region_tree.get_checked()]
        self.show_seg()

    def show_seg(self):
        self.slice_viewer.axes[0].cla()
        seg_img = self.currTarget.get_img(seg="visualign")
        seg = self.currTarget.seg_visualign
        data_regions = np.zeros_like(seg)
        for roi in self.rois: data_regions += (seg==roi).astype(int)
        data_regions = np.multiply(data_regions, seg)
        self.slice_viewer.axes[0].imshow(ski.color.label2rgb(
            data_regions,
            seg_img, 
            bg_label=0,
            bg_color=None,
            saturation=1,
            alpha=.7,
            image_alpha=1,
            colors=self.region_colors
        ))
        self.slice_viewer.update()
    
    def on_move(self, event):
        if event.inaxes:
            x,y = int(event.xdata), int(event.ydata)
            id = self.currTarget.seg_visualign[y,x]
            name = self.get_region_name(id)
            self.slice_viewer.axes[0].set_title(name)
            self.slice_viewer.update()
        
    def on_click(self, event=None):
        if event.inaxes:
            x,y = int(event.xdata), int(event.ydata)
            id = float(self.currTarget.seg_visualign[y,x])
            if self.region_tree.tag_has("checked", id):
                self.region_tree._uncheck_descendant(id)
                self.region_tree._uncheck_ancestor(id)
            else:
                self.region_tree._check_ancestor(id)
                self.region_tree._check_descendant(id)
            self.update()
            
    def get_slide_index(self):
        return self.curr_slide_var.get()-1
    
    def get_target_index(self):
        return self.curr_target_var.get()-1
    
    def get_region_name(self, id):
        region_df = self.atlases['names']
        return region_df.loc[region_df.id==id].index[0]

    def cancel(self):
        super().cancel()

    def done(self):
        for slide in self.slides:
            for target in slide.targets:
                for roi in self.rois:
                    roi_name = self.get_region_name(roi)
                    pts = np.argwhere(target.seg_visualign==roi)
                    if pts.shape[0] == 0: continue # skip if no points found
                
                    _,labels = dbscan(pts, eps=2, min_samples=5, metric='manhattan')
                    for l in set(labels):
                        if l == -1: continue # these points dont belong to any clusters
                        cluster = pts[labels==l]
                        shape_name = f'{roi_name}_{l}'

                        hull = shapely.concave_hull(shapely.MultiPoint(cluster), 0.1) # get hull for cluster
                        
                        # only hulls defined as polygons can actually be cut out, other hulls will not be shown
                        if hull.geom_type == 'Polygon':
                            bound = shapely.get_coordinates(hull)
                            target.region_boundaries[shape_name] = bound
        super().done()

    class ModifiedCheckboxTreeView(ttkwidgets.CheckboxTreeview):

        def __init__(self, master=None, **kw):
            super().__init__(master, **kw)

        def get_checked(self):
            """Overloading """
            checked = []

            def get_checked_children(item):
                if not self.tag_has("unchecked", item):
                    ch = self.get_children(item)
                    if self.tag_has("checked", item):
                        checked.append(item)
                    if ch:
                        for c in ch:
                            get_checked_children(c)

            ch = self.get_children("")
            for c in ch:
                get_checked_children(c)
            return checked

class Exporter(Page):

    def __init__(self, master, slides, atlases):
        super().__init__(master, slides, atlases)
        self.header = "Exporting Boundaries."
        self.currSlide = None
        self.exported = []
        self.numOutputs = []

    def activate(self):
        self.slide_nav_combo.config(
            values=[i+1 for i in range(len(self.slides))]
        )
        self.exported = [[1 for t in slide.targets] for slide in self.slides] # 1 for not exported, 2 for exported, negative for current export group
        self.numOutputs = [0 for slide in self.slides]
        super().activate()

    def create_widgets(self):
        # menu
        self.menu_frame = tk.Frame(self)
        self.toggle_all_btn = ttk.Button(
            master=self.menu_frame,
            text='',
            command = self.toggle_select
        )
        self.export_btn = ttk.Button(
            master=self.menu_frame,
            text="Export",
            command=self.export,
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
        self.slide_viewer = TkFigure(self.slides_frame, toolbar=True)
        self.slide_viewer.canvas.mpl_connect('button_press_event', self.on_click)

    def show_widgets(self):
        
        self.update() # update buttons, slideviewer, stalign params

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # show menu
        self.menu_frame.grid(row=0, column=0, columnspan=2, sticky='nsew')
        self.slide_nav_combo.pack(side=tk.RIGHT)
        self.slide_nav_label.pack(side=tk.RIGHT)

        self.toggle_all_btn.pack(side=tk.LEFT)
        self.export_btn.pack(side=tk.TOP)

        # show slide viewer
        self.slides_frame.grid(row=1, column=0, sticky='nsew')
        self.slide_viewer.get_widget().pack(side=tk.LEFT, expand=True, fill=tk.BOTH)

    def update(self, event=None):
        self.currSlide = self.slides[self.get_index()]
        self.slide_viewer.axes[0].cla() # clear and show new slide image
        self.update_buttons() # update buttons
        self.show_slide()

    def update_buttons(self):
        self.toggle_all_btn.config(text="Select All")
        self.export_btn.config(state='disabled')
        for export_status in self.exported[self.get_index()]:
            if export_status < 0: 
                self.toggle_all_btn.config(text="Deselect All")
                self.export_btn.config(state='active')
                return
        
    def show_slide(self):
        self.slide_viewer.axes[0].imshow(self.currSlide.get_img())
        for i,target in enumerate(self.currSlide.targets):
            edgecolor = NEW_COLOR
            if self.exported[self.get_index()][i] < 0: edgecolor = REMOVABLE_COLOR
            elif self.exported[self.get_index()][i] == 2: edgecolor = COMMITTED_COLOR
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
        self.slide_viewer.update()
    
    def on_click(self, event=None):
        if event.inaxes is None: return
        x,y = int(event.xdata), int(event.ydata)
        if event.button == 1:
            for i,target in enumerate(self.currSlide.targets):
                if (target.x_offset <= x <= target.x_offset + target.img_original.shape[1] and 
                    target.y_offset <= y <= target.y_offset + target.img_original.shape[0]):
                    self.exported[self.get_index()][i] *= -1
                    self.update()
                    return
                    

    def export(self, event=None):
        # reorders them so that first point is top left, second is 
        cp_sorted = self.currSlide.calibration_points.copy()
        cp_sorted.sort()
        cp_sorted[1:] = sorted(cp_sorted[1:], key=lambda a:a[1])

        slide_index = self.get_index()
        output_filename = f'{os.path.splitext(self.currSlide.filename)[0]}_output_{self.numOutputs[slide_index]}.xml'
        self.numOutputs[slide_index] += 1
        with open(output_filename,'w') as file:
            file.write("<ImageData>\n")
            file.write("<GlobalCoordinates>1</GlobalCoordinates>\n")
            
            for i,pt in enumerate(cp_sorted):
                file.write(f"<X_CalibrationPoint_{i+1}>{pt[0]}</X_CalibrationPoint_{i+1}>\n")
                file.write(f"<Y_CalibrationPoint_{i+1}>{pt[1]}</Y_CalibrationPoint_{i+1}>\n")
            
            file.write(f"<ShapeCount>{sum([len(t.region_boundaries) for t in self.currSlide.targets])}</ShapeCount>\n")
            numShapesExported = 0
            for ti,t in enumerate(self.currSlide.targets):
                if self.exported[self.get_index()][ti] > 0: continue
                self.exported[self.get_index()][ti] = 2
                self.write_target_shapes(file, t, ti, numShapesExported)
                numShapesExported += len(t.region_boundaries)
            file.write("</ImageData>")
        self.update()
    
    def write_target_shapes(self, file, target, targetIndex, numShapesExported):
        for i,(name,shape) in enumerate(target.region_boundaries.items()):
            file.write(f'<Shape_{numShapesExported + i + 1}>\n')
            file.write(f'<PointCount>{len(shape)+1}</PointCount>\n')
            file.write(f'<TransferID>{name}_{targetIndex}</TransferID>\n')

            for j in range(len(shape)+1):
                file.write(f'<X_{j+1}>{shape[j%len(shape)][1]+target.x_offset}</X_{j+1}>\n')
                file.write(f'<Y_{j+1}>{shape[j%len(shape)][0]+target.y_offset}</Y_{j+1}>\n')
            
            file.write(f'</Shape_{numShapesExported + i + 1}>\n')

    def toggle_select(self, event=None):
        currSlide_exported = self.exported[self.get_index()]
        has_neg = False # boolean whether currSlide_exported contains a value < 0
        for export_status in currSlide_exported:
            if export_status < 0: 
                has_neg = True
                break
        
        for i in range(len(currSlide_exported)):
            if currSlide_exported[i] < 0 or not has_neg: currSlide_exported[i] *= -1
        self.update()

    def get_index(self):
        return self.curr_slide_var.get()-1

    def done(self):
        super().done()
    
    def cancel(self):
        super().cancel()

    