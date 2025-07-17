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
from datetime import datetime

from images import *
from constants import *
from utils import *

from abc import ABC, abstractmethod

class Page(tk.Frame, ABC):
    """
    Abstract base class for all pages in the application.
    Each page should inherit from this class and implement the abstract methods.
    
    
    Attributes
    ----------
        master : tk.Frame
            The parent window.
        project : dict 
            The project data containing slides and atlases.
        slides : list
            List of Slide objects.
        atlases : dict 
            Dictionary containing atlas information.
        header : str
            Header text for the page.
        
    Parameters
    ----------
        master : tk.Frame 
            The parent window.
        project : dict
            The project data containing slides and atlases.
    """

    def __init__(self, master, project):
        super().__init__(master)
        self.project = project
        self.slides = project['slides']
        self.atlases = project['atlases']
        self.header = ""
        self.create_widgets()

    @abstractmethod
    def create_widgets(self): 
        """
        Abstract method to create widgets for the page. Each subclass should
        implement this method to create its own widgets. This method is
        responsible for initializing and setting up all widgets that will be
        used on the page. Widgets should be configured here, but not packed or
        gridded; layout should be handled in show_widgets().
        """
        pass

    @abstractmethod
    def show_widgets(self): 
        """
        Abstract method to show the widgets on the page. Each subclass should
        implement this method to arrange and display its widgets. This method is
        responsible for laying out and displaying all widgets that belong to the
        page, using the preferred geometry manager.
        """
        pass

    def activate(self):
        """
        Activate the page by packing it into the parent frame and displaying its
        widgets. This method should be called when the page is to be displayed.
        Subclasses may add extra functionality to this method as needed.
        """
        self.pack(expand=True, fill=tk.BOTH)
        self.show_widgets()
    
    def deactivate(self):
        """
        Deactivate the page by hiding it. This method should be called when the
        page is no longer needed. It will remove the page from the view, but not
        destroy it. Subclasses may override this method to add additional
        cleanup functionality.
        """
        self.pack_forget()
    
    @abstractmethod
    def done(self):
        """
        Abstract method to finalize the page's actions. This method is called
        when the user presses the "Next" button. The user has completed their
        actions on the page and is ready to proceed. It should handle any
        necessary validation or data processing before moving to the next page.
        This method should also deactivate the page.
        """
        self.deactivate()

    @abstractmethod
    def cancel(self):
        """
        Abstract method to cancel the page's actions. This method is called when
        the user presses the "Previous" button. It should handle any necessary
        cleanup or state reset before returning to the previous page or exiting
        the application. This method should also deactivate the page.
        """
        self.deactivate()

    def get_header(self):
        """
        Returns the header text for the page.

        Returns
        -------
        self.header : str
            The header text for the page.
        """
        return self.header

class Starter(Page):
    """
    Page for selecting the atlas and slides to process.
    This page allows the user to choose an atlas and a folder containing
    sample images. It initializes the atlas and slide information, and
    sets up the project structure.
    """

    def __init__(self, master, project):
        super().__init__(master, project)
        self.header = 'Select samples and atlas'
    
    def create_widgets(self):
        """
        Create widgets for the Starter page. This includes:
        - Atlas picker: A combobox to select an atlas from available atlases.
        - Slides picker: An entry field to select a folder containing sample images.
        - Browse button: A button to open a file dialog for selecting the slides folder.
        """
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
        """
        Show the widgets for the Starter page. This method arranges the widgets
        in a grid layout and configures their appearance.
        """

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
        """
        Open a file dialog to select a folder containing sample images.
        """
        folder_name = tk.filedialog.askdirectory(
            parent=self, 
            initialdir=os.curdir,
            mustexist=True
        )
        self.slides_folder_name.set(folder_name)
    
    def done(self):
        """
        Finalize the Starter page's actions. This method checks that the user
        has selected an atlas and a folder containing sample images. It then
        loads the atlas information and the slides into the project structure.
        Raises an exception if the atlas or slides folder is not selected.
        """
        # check that atlas picker and slides picker are not blank
        if self.atlas_name.get() == 'Choose Atlas': 
            raise Exception('Must select an atlas.')
        elif self.slides_folder_name.get() == '':
            raise Exception('Must select an folder containing sample images.')

        # load atlases
        atlas_folder_name = os.path.join('atlases', self.atlas_name.get())
        self.load_atlas_info(atlas_folder_name)

        # load slides
        path = self.slides_folder_name.get()
        if not os.path.exists(path): 
            raise Exception(
                'Could not find slides folder at the specified path: ' + path
            )
        self.load_slides(path)

        # create project folder
        folder = "DART-" + datetime.now().strftime("%Y-%m-%d_%H%M%S")
        os.mkdir(os.path.join(path, folder))
        self.project['parent_folder'] = os.path.abspath(path)
        self.project['folder'] = os.path.join(
            self.project['parent_folder'], 
            folder
        )

        super().done()

    def load_atlas_info(self, path):
        """
        Load atlas information from the specified path. This method searches for
        the atlas files in the given directory and initializes the atlases
        with the reference and label images. It also loads the names dictionary
        for the atlas.
        
        Parameters
        ----------
        path : str
            The path to the atlas directory containing the reference and label images.
        """
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

        # load images for downscaled version, 
        # which should be at least 50 microns per pixel
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
        self.atlases['names'] = pd.read_csv(
            names_dict_filename, 
            index_col='name'
        )
        self.atlases['names'].loc['empty','id'] = 0

    def load_slides(self, path):
        """
        Load slides from the specified path. This method searches for image files
        in the given directory and initializes Slide objects for each image file.
        It also creates a new folder for the project based on the current date and
        time.
        
        Parameters
        ----------
        path : str
            The path to the directory containing the sample images.
        """
        for f in os.listdir(path):
            curr_path = os.path.join(path, f)
            isImage = curr_path.lower().endswith(
                ('.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp', '.gif')
            )
            if os.path.isfile(curr_path) and isImage:
                new_slide = Slide(curr_path)
                self.slides.append(new_slide)
        
        # TODO: raise exception if no slides found

    def cancel(self):
        """
        Cancel the actions on the Starter page.
        """
        super().cancel()

class SlideProcessor(Page):
    """
    Page for processing slides and selecting calibration points. This page allows the
    user to select slices and calibration points on the slides. It provides tools for
    adding, removing, and committing calibration points and target regions. The user
    can also switch between slides and adjust the annotation mode (point or rectangle).
    """

    def __init__(self, master, project):
        """
        Initialize the SlideProcessor page with the given master and project.

        Parameters
        ----------
        master : tk.Frame
            The parent window for the page.
        project : dict
            The project data containing slides and atlases.
        """
        super().__init__(master, project)
        self.header = "Select slices and calibration points."
        self.currSlide = None

        self.newPointX = self.newPointY = -1
        self.newTargetX = self.newTargetY = -1
        self.newTargetData = None

        # matplotlib rectangle selector for selecting slices
        self.slice_selector = mpl.widgets.RectangleSelector(
            self.slide_viewer.axes[0], 
            self.on_select,
            button=1,
            useblit=True,
            interactive=True
        )

    def create_widgets(self):
        """
        Create widgets for the SlideProcessor page. This includes:
        - Menu frame: Contains controls for annotation mode, buttons for adding/removing
          points and targets, and slide navigation.
        - Slide viewer: A matplotlib figure for displaying the current slide
        - Slide navigation: A combobox for selecting the current slide.
        """

        # menu
        self.menu_frame = tk.Frame(self)

        # annotation mode controls
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
        
        # menu buttons for adding/removing/clearing points and targets
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
        # TODO: "clear all" button to clear all targets or points from current slide

        # slide navigation
        self.slide_nav_label = ttk.Label(self.menu_frame, text="Slide: ")
        self.curr_slide_var = tk.IntVar(master=self.menu_frame, value='1')
        self.slide_nav_combo = ttk.Combobox(
            master=self.menu_frame,
            values=[],
            state='readonly',
            textvariable=self.curr_slide_var,
        )
        self.slide_nav_combo.bind('<<ComboboxSelected>>', self.refresh)

        # slide viewer
        self.slides_frame = tk.Frame(self)
        self.slide_viewer = TkFigure(self.slides_frame, toolbar=True)

    def activate(self):
        """
        Activate the SlideProcessor page. This method sets up the initial state
        of the page, including the current slide and annotation mode. It also
        connects the click event to the slide viewer for adding calibration points
        and selecting slices. If the annotation mode is set to 'point', it activates
        point mode; if set to 'rect', it activates rectangle mode.
        """
        self.refresh() # update buttons, slideviewer
        if self.annotation_mode.get() == 'point':
            self.activate_point_mode()
        elif self.annotation_mode.get() == 'rect':
            self.activate_rect_mode()
        super().activate()

    def show_widgets(self):
        """
        Show the widgets for the SlideProcessor page. This method arranges the
        widgets in a grid layout and configures their appearance. It sets up the
        grid for the menu and slide viewer, and packs the widgets into their respective
        frames.
        """

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
        """
        Show the current slide in the slide viewer. This method updates the
        slide viewer with the current slide's image and draws rectangles for
        the targets and calibration points. It also highlights the current
        calibration points and targets with different colors.
        
        Parameters
        ----------
        event : tk.Event, optional
            The event that triggered the update (default is None).
        """
        #TODO: confirm that removing event=None does not break anything
        
        # clear the axes and show the current slide image
        self.slide_viewer.axes[0].cla()
        self.slide_viewer.axes[0].imshow(self.currSlide.get_img())
        
        # draw rectangles for targets
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
        
        # draw calibration points
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

    def refresh(self, event=None):
        """
        Refresh the page by updating slide index, clearing uncommitted targets and points,
        and updating slide viewer and buttons.

        Parameters
        ----------
        event : tk.Event, optional
            The event that triggered the update (default is None).
        """
        self.currSlide = self.slides[self.get_index()]
        self.clear() # clear and show new slide image
        self.update_buttons() # update buttons

    def update_buttons(self):
        """
        Update the text and state of the buttons based on the current annotation mode
        and the current slide's targets and calibration points. This method enables or
        disables the remove, commit, and clear buttons based on whether there are
        targets or calibration points to add or remove.
        """
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

    def on_select(self, click, release):
        """
        Callback for the rectangle selector. This method is called when the user
        selects a rectangle on the slide viewer in "rect" mode. If the selection
        is a valid rectangle (i.e., the start and end points are different), it
        updates the new target coordinates and data based on the selected rectangle.
        
        Parameters
        ----------
        click : mpl.backend_bases.MouseEvent
            The mouse event for the click action.
        release : mpl.backend_bases.MouseEvent
            The mouse event for the release action.
        """
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
        """
        Callback for mouse click events on the slide viewer. This method is called
        when the user clicks on the slide viewer in "point" mode. If the click is within
        the axes, it updates the new point coordinates based on the click position.
        
        Parameters
        ----------
        event : mpl.backend_bases.MouseEvent
            The mouse event for the click action.
        """

        if event.inaxes is None: return
        x,y = int(event.xdata), int(event.ydata)
        if event.button == 1:
            self.newPointX = x
            self.newPointY = y

        self.update_buttons()
        self.show_slide() # TODO: speed up software by not redrawing the entire slide every time a point is added

    def activate_point_mode(self):
        """
        Activate point mode for adding calibration points. This method clears the
        current slide's uncommitted target and point data, connects click event for
        adding calibration points, disconnects the rectangle selector, and updates the
        buttons.
        """
        self.clear()
        self.slice_selector.set_active(False)
        self.click_event = self.slide_viewer.canvas.mpl_connect('button_press_event', self.on_click)
        self.update_buttons()

    def activate_rect_mode(self):
        """
        Activate rectangle mode for selecting slices. This method clears the
        current slide's uncommitted target and point data, connects the rectangle
        selector for selecting slices, disconnects the click event, and updates
        the buttons.
        """
        self.clear()
        self.slice_selector.set_active(True)
        self.slide_viewer.canvas.mpl_disconnect(self.click_event)
        self.update_buttons()

    def remove(self):
        """
        Remove the currently selected target or point based on the annotation mode.
        """

        mode = self.annotation_mode.get()
        if mode == 'rect':
            self.currSlide.remove_target()
        elif mode == 'point':
            self.currSlide.remove_calibration_point()
        else: return

        self.show_slide()
        self.update_buttons

    def commit(self):
        """
        Commit the current target or point based on the annotation mode.
        """

        mode = self.annotation_mode.get()
        if mode == 'rect':
            if self.newTargetData is None: return
            self.currSlide.add_target(
                self.newTargetX, 
                self.newTargetY,
                self.newTargetData 
            )
            self.newTargetData = None
            self.newTargetX = self.newTargetY = -1
            self.slice_selector.clear()
        elif mode == 'point':
            self.currSlide.add_calibration_point(
                [self.newPointX,self.newPointY]
            )
            self.newPointX = self.newPointY = -1
        else: return
        
        self.show_slide()
        self.update_buttons()

    def clear(self):
        """
        Clear the current slide's uncommitted target and point data and show the current
        slide image.
        """
        self.newTargetX = self.newTargetY = -1
        self.newPointX = self.newPointY = -1
        self.newTargetData = None
        self.slice_selector.clear()
        self.show_slide()

    def get_index(self):
        """
        Get the index of the current slide based on the selected value in the
        slide navigation combobox.

        Returns
        -------
        index : int
            The index of the current slide.
        """
        return self.curr_slide_var.get()-1

    def done(self):
        """
        Finalize the SlideProcessor page's actions. This method checks that each slide
        has at least one target and exactly three calibration points. If any slide does
        not meet these criteria, it raises an exception with an error message. It also
        saves the target coordinates and calibration points in text files, and saves the
        target images in the project folder.
        
        Raises
        -------
        Exception
            If any slide does not have at least one target or exactly three calibration points.
        """
        # TODO: if no targets selected, show warning and ask if user wants to use entire image as target, 
        # ^maybe also have option to just skip this image?

        for i,slide in enumerate(self.slides):
            e = None
            if slide.numTargets < 1: 
                e = Exception(f"No targets selected for slide #{i+1}")
            
            if slide.numCalibrationPoints != 3:
                e = Exception(f"Slide #{i+1} must have exactly 3 calibration points, found {slide.numCalibrationPoints}")
            else:
                # reorder calibration points so that first point is top left,
                # second is top right, and third is bottom left
                slide.calibration_points.sort()
                slide.calibration_points[1:] = sorted(
                    slide.calibration_points[1:], 
                    key=lambda point: point[1]
                )

            # if there was an error, set the current slide to the one with the error
            # and show the error message
            if e is not None:
                self.curr_slide_var.set(i+1)
                self.refresh()
                tk.messagebox.showerror(
                    title="Error",
                    message=str(e)
                )
                raise e

        # save target coordinates in a text file
        with open(os.path.join(self.project['folder'], 'target_coordinates.txt'), 'w') as f:
            f.write("slide#_target# : X Y\n")
            for si, slide in enumerate(self.slides):
                for ti, target in enumerate(slide.targets):
                    f.write(f"{get_filename(si, ti)} : {target.x_offset} {target.y_offset}\n")

        # save calibration points in a text file
        with open(os.path.join(self.project['folder'], 'calibration_points.txt'), 'w') as f:
            f.write("slide# : X Y\n")
            for si, slide in enumerate(self.slides):
                for point in slide.calibration_points:
                    f.write(f"{si} : {point[0]} {point[1]}\n")
        
        # save target images in the project folder
        for si, slide in enumerate(self.slides):
            for ti, target in enumerate(slide.targets):
                filename = get_filename(si, ti)+'.jpg'
                ski.io.imsave(os.path.join(self.project['folder'], filename),target.img_original)

        super().done()

    def cancel(self):
        """
        Cancel the actions on the SlideProcessor page. This method clears the
        current slide's uncommitted target and point data, disconnects the click
        event and rectangle selector, and calls the parent class's cancel method
        to finalize the page's actions.
        """
        self.slides.clear()
        # TODO: decide whether to clear the points/target data
        super().cancel()

class TargetProcessor(Page):
    """
    Page for selecting landmark points and adjusting affine transformations.
    This page allows the user to select landmark points on the atlas and adjust
    affine transformations based on the selected points. It provides tools for
    adding, removing, and committing landmark points, as well as adjusting the
    affine transformations using rotation and translation scales.
    """

    # TODO: add feature to select between rotation/translation control and landmark annotation mode
    # during rotation/translation, use low resolution atlas images

    def __init__(self, master, project):
        super().__init__(master, project)
        self.header = "Select landmark points and adjust affine."
        self.currSlide = None
        self.currTarget = None
        self.new_points = [[],[]]
        self.point_size = 4

    def create_widgets(self):
        """
        Create widgets for the TargetProcessor page. This includes:
        - Menu frame: Contains controls for slide and target navigation, buttons for
          removing and committing points, and clearing uncommitted points.
        - Slice frame: Contains the slice viewer for displaying the atlas images
          and the rotation and translation controls.
        - Parameter settings frame: Contains controls for adjusting parameters for
          automatic alignment, including basic and advanced parameter settings.
         """
        
        # menu frame with slide and target navigation, buttons, and controls
        self.menu_frame = tk.Frame(self)

        # slide navigation
        self.slide_nav_label = ttk.Label(self.menu_frame, text="Slide: ")
        self.curr_slide_var = tk.IntVar(master=self.menu_frame, value='1')
        self.slide_nav_combo = ttk.Combobox(
            master=self.menu_frame,
            values=[],
            state='readonly',
            textvariable=self.curr_slide_var,
        )
        self.slide_nav_combo.bind('<<ComboboxSelected>>', self.switch_slides)

        # target navigation
        self.target_nav_label = ttk.Label(self.menu_frame, text="Target: ")
        self.curr_target_var = tk.IntVar(master=self.menu_frame, value='1')
        self.target_nav_combo = ttk.Combobox(
            master=self.menu_frame,
            values=[],
            state='readonly',
            textvariable=self.curr_target_var,
        )
        self.target_nav_combo.bind('<<ComboboxSelected>>', self.update)

        # landmark annotation controls
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

        # slice frame with viewer and controls
        self.slice_frame = tk.Frame(self)

        # slice viewer for displaying atlas images
        self.figure_frame = tk.Frame(self.slice_frame)
        self.slice_viewer = TkFigure(self.figure_frame, num_cols=2, toolbar=True)
        self.click_event = self.slice_viewer.canvas.mpl_connect('button_press_event', self.on_click)

        # rotation controls
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

        # translation controls
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

    def activate(self):
        """
        Activate the TargetProcessor page. This method sets up the initial state
        of the page, including the current slide and target. It also updates the
        atlas images and sets the pixel dimensions for the target images. It
        configures the translation scale based on the atlas pixel locations.
        """

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

    def show_widgets(self):
        """
        Show the widgets for the TargetProcessor page. This method arranges the
        widgets in a grid layout and configures their appearance. It sets up the
        grid for the menu, slice viewer, rotation and translation controls, and
        parameter settings. It also packs the widgets into their respective frames.
        """
        
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
        """
        Update the current slide and target based on the selected values in the
        slide and target navigation comboboxes. This method retrieves the current
        slide and target based on the selected indices, updates the slide and target
        navigation comboboxes, and sets the current target's theta values and
        translation value. It also resets the new points and updates the target
        and atlas images in the slice viewer.
        
        Parameters
        ----------
        event : tk.Event, optional
            The event that triggered the update (default is None).
        """
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
        """
        Switch to the selected slide in the slide navigation combobox. This method
        retrieves the selected slide index from the combobox, updates the current
        slide, and updates the target navigation combobox to reflect the targets
        available for the selected slide. It also resets the new points and updates
        the target and atlas images in the slice viewer.
        
        Parameters
        ----------
        event : tk.Event, optional
            The event that triggered the switch (default is None).
        """
        self.curr_target_var.set(1) # reset target index to 1
        self.update()

    def show_target(self):
        """
        Show the current target image in the slice viewer. This method clears
        the axes for the target image, sets the title, and displays the target
        image with the appropriate colormap. It also highlights the new point
        and the committed and removable landmark points with different colors.
        """
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
        """
        Update the estimated image for the target based on the current affine
        transformation parameters. This method retrieves the atlas for the current
        target, applies the affine transformation to the atlas pixel locations,
        and transforms the slice image using the target's affine transformation
        parameters. It then updates the target's estimated image with the transformed
        slice image.
        
        Parameters
        ----------
        target : Target
            The target for which to update the estimated image.
        """

        atlas = self.atlases[DSR]
        
        xE = [ALPHA*x for x in atlas.pix_loc]
        XE = np.stack(np.meshgrid(np.zeros(1),xE[1],xE[2],indexing='ij'),-1)
        L,T = target.get_LT()
        slice_transformed = (L @ XE[...,None])[...,0] + T
        slice_img = atlas.get_img(slice_transformed)
        
        target.img_estim.load_img(slice_img)

    def show_atlas(self, event=None):
        """
        Show the atlas image in the slice viewer. This method clears the axes for
        the atlas image, sets the title, and displays the atlas image with the
        appropriate colormap. It also highlights the new point and the committed
        and removable landmark points with different colors. It updates the affine
        transformation parameters based on the current rotation and translation
        values, and applies the affine transformation to the atlas pixel locations.
        """
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
        """
        Update the state of the buttons based on the current target's landmarks
        and the new points selected by the user. This method enables or disables
        the remove, commit, and clear buttons based on whether there are landmarks
        to remove, new points to add, or existing points to clear. It also ensures
        that the buttons are only active when there are changes to save.
        """
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
        """
        Callback for mouse click events on the slice viewer. This method is called
        when the user clicks on the slice viewer to select landmark points. It checks
        if the click is within the axes, retrieves the new point coordinates based on
        the click position, and updates the new points for the target and atlas images.
        """
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
        """
        Remove the currently selected landmark points from the current target.
        This method checks if the current target has any landmarks to remove. If
        there are landmarks, it removes the last landmark point from both the target
        and atlas images, updates the new points, and refreshes the display.
        """
        self.currTarget.remove_landmarks()
        self.update()

    def commit(self):
        """
        Commit the new landmark points to the current target. This method checks if
        there are new points selected for both the target and atlas images. If there
        are new points, it adds the new points to the current target's landmarks for
        both the target and atlas images, clears the new points, and updates the display.
        """

        self.currTarget.add_landmarks(self.new_points[0], self.new_points[1])
        self.new_points = [[],[]]
        self.update()

    def clear(self):
        """
        Clear the new points selected for the target and atlas images. This method
        resets the new points to empty lists, updates the display, and refreshes the
        buttons to reflect the cleared state.
        """

        self.new_points = [[],[]]
        self.update()
    
    def save_params(self):
        """
        Save the current parameters for the current target. This method retrieves
        the parameter values from the advanced entries, updates the current target's
        parameters with the new values, and sets the basic settings based on the
        current target's parameters. It also prints a confirmation message indicating
        that the parameters have been saved.
        """
        for key, value in self.param_vars.items():
            self.currTarget.set_param(key, float(value.get()))
        self.set_basic()
        # confirm
        print("parameters saved!")

    def basic_to_advanced(self, event=None):
        """
        Convert the basic settings selected in the combobox to advanced parameters.
        This method retrieves the selected basic setting from the combobox, resets
        the advanced parameters to their default values, and sets the iterations
        based on the selected speed setting. It updates the advanced entries with
        the new values and prints a confirmation message indicating that the parameters
        have been reset to the defaults.
        """

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

    def set_basic(self):
        """
        Set the basic settings based on the current target's parameters.
        This method checks the current target's parameters and updates the basic
        settings combobox to reflect the estimated time for the selected number of
        iterations. If the parameters do not match the default values, it sets the
        basic settings to "Advanced settings estimated X" where X is the estimated
        time based on the number of iterations. If the parameters match the default
        values, it sets the basic settings to one of the predefined options based on
        the number of iterations.
        """
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
        """
        Finalize the TargetProcessor page's actions. This method uses the atlas
        image estimation to estimate the pixel dimensions for each target,
        creates folders for each target, and writes the affine parameters, landmark
        points, and stalign parameters to text files in the respective target folders.
        """
        
        # estimate pixel dimensions
        for si, slide in enumerate(self.slides):
            slide.estimate_pix_dim()
            for ti,target in enumerate(slide.targets):
                folder = os.path.join(
                    self.project['folder'], 
                    get_folder(si, ti, self.project['stalign_iterations'])
                )
                os.mkdir(folder)

                with open(os.path.join(folder, 'settings.txt'), 'w') as f:
                    # write affine parameters
                    f.write("AFFINE\n")
                    f.write(f"rotations : {target.thetas[0]} {target.thetas[1]} {target.thetas[2]}\n")
                    f.write(f"translation : {target.T_estim[0]} {target.T_estim[1]} {target.T_estim[2]}\n")
                    f.write("\n")

                    # write landmark points
                    f.write("LANDMARKS\n")
                    f.write("target point: atlas point\n")
                    for i in range(target.num_landmarks):
                        target_pt = target.landmarks['target'][i]
                        atlas_pt = target.landmarks['atlas'][i]
                        f.write(f"{target_pt[0]} {target_pt[1]} : {atlas_pt[0]} {atlas_pt[1]}\n")
                    f.write("\n")

                    # write stalign parameters
                    f.write("PARAMETERS\n")
                    f.write("parameter : value\n")
                    for key, value in target.stalign_params.items():
                        f.write(f"{key} : {value}\n")

        super().done()

    def cancel(self):
        """
        Cancel the actions on the TargetProcessor page. This method clears the
        current target's affine estimation and landmark points, resets the parameters,
        and calls the parent class's cancel method to finalize the page's actions.
        """

        # clear affine, landmark points, and stalign parameters
        for slide in self.slides:
            for target in slide.targets:
                target.set_param() # reset params
                target.thetas = np.array([0, 0, 0])
                target.T_estim = np.array([0, 0, 0])
                target.img_estim = Image()
                for i in range(target.num_landmarks): target.remove_landmarks()
        super().cancel()
    
    def isFloat(self, str):
        """
        Check if a string can be converted to a float.

        Parameters
        ----------
        str : str
            The string to check.
        
        Returns
        -------
        bool
            True if the string can be converted to a float, False otherwise.
        """
        try:
            float(str)
            return True
        except ValueError:
            return False

    def get_slide_index(self):
        """
        Get the index of the current slide based on the selected value in the
        slide navigation combobox. The index is adjusted to be zero-based by
        subtracting 1 from the selected value.
        
        Returns
        -------
        index : int
            The index of the current slide.
        """
        return self.curr_slide_var.get()-1
    
    def get_target_index(self):
        """
        Get the index of the current target based on the selected value in the
        target navigation combobox. The index is adjusted to be zero-based by 
        subtracting 1 from the selected value.
        
        Returns
        -------
        index : int
            The index of the current target.
        """
        return self.curr_target_var.get()-1

class STalignRunner(Page):

    def __init__(self, master, project):
        super().__init__(master, project)
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

        transform = LDDMM_3D_LBFGS(
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
        if self.slides[0].targets[0].transform is None:
            raise Exception("ERROR! Must Run STalign before advancing")
        super().done()
    
    def cancel(self):
        self.results_viewer.pack_forget()
        for slide in self.slides:
            for target in slide.targets:
                target.transform = None
                target.seg_stalign = None
        super().cancel()

class VisuAlignRunner(Page):

    def __init__(self, master, project):
        super().__init__(master, project)
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

        self.project_folder = self.project['folder']
        visualign_export_folder = os.path.join(self.project_folder,'EXPORT_VISUALIGN_HERE')
        if not os.path.exists(visualign_export_folder):
            os.mkdir(visualign_export_folder)

        with open(os.path.join(self.project_folder,'CLICK_ME.json'),'w') as f:
            f.write('{')
            f.write('"name":"", ')
            f.write('"target":"custom_atlas.cutlas", ')
            f.write('"aligner": "prerelease_1.0.0", ')
            f.write('"slices": [')
            i=0
            for sn,slide in enumerate(self.slides):
                for ti,t in enumerate(slide.targets):
                    filename = get_filename(sn, ti)+'.jpg'
                    f.write('{')
                    h = raw_stack[i].shape[0]
                    w = raw_stack[i].shape[1]
                    f.write(f'"filename": "{filename}", ')
                    f.write(f'"anchoring": [0, {len(raw_stack)-i-1}, {h}, {w}, 0, 0, 0, 0, -{h}], ')
                    f.write(f'"height": {h}, "width": {w}, ')
                    f.write('"nr": 1, "markers": []}')
                    if i < len(raw_stack)-1: f.write(',')
                    i += 1
            f.write(']}')
        
        super().activate()

    def deactivate(self):
        os.remove(os.path.join(self.project_folder,'CLICK_ME.json'))
        os.remove('VisuAlign-v0_9/custom_atlas.cutlas/labels.nii.gz')
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
                visualign_nl_flat_filename = os.path.join(self.project_folder,
                                                          "EXPORT_VISUALIGN_HERE",
                                                          get_filename(sn,ti)+"_nl.flat")
                try:
                    print(f'we are looking for {visualign_nl_flat_filename}')
                    with open(visualign_nl_flat_filename, 'rb') as fp:
                        buffer = fp.read()
                except:
                    print(f"visualign manual alignment not performed for slice #{sn}, target #{ti}, using stalign semiautomatic alignment")
                    t.seg_visualign = t.seg_stalign.copy()
                    continue
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

    def __init__(self, master, project):
        super().__init__(master, project)
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

    def __init__(self, master, project):
        super().__init__(master, project)
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
        # TODO: show the shapes being exported
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

        slide_index = self.get_index()
        output_filename = f'{os.path.splitext(self.currSlide.filename)[0]}_output_{self.numOutputs[slide_index]}.xml'
        output_path = os.path.join(self.project['folder'], "output", output_filename)
        self.numOutputs[slide_index] += 1

        with open(output_path,'w') as file:
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
