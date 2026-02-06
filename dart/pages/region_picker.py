import json
import numpy as np
import os
import pandas as pd
import skimage as ski
from sklearn.cluster import dbscan
import shapely
import tkinter as tk
from tkinter import ttk
import ttkwidgets

from dart.pages.base import BasePage
from dart.utils import TkFigure

class RegionPicker(BasePage):
    """
    Page for selecting regions of interest (ROIs) from the atlas.
    This page allows the user to select regions from a tree view
    of the atlas regions and visualize the selected regions on
    the target images.
    """

    def __init__(self, master, project):
        super().__init__(master, project)
        self.header = "Selecting ROIs"
        self.currSlide = None
        self.currTarget = None
        self.rois = []
        self.region_colors = ['red','yellow','green','orange','brown','white','black','grey','cyan','pink','tan']
    
    def activate(self):
        """
        Activate the RegionPicker page. This method initializes the
        region tree view with the atlas regions, sets up the slide and
        target navigation comboboxes, and ensures the widgets are displayed.
        It also calls `make_tree` to populate the region tree with the
        atlas regions if it hasn't been done yet.
        """
        self.slide_nav_combo.config(
            values=[i+1 for i in range(len(self.slides))]
        )

        if len(self.region_tree.get_children()) == 0:
            self.make_tree()

        super().activate()
    
    def deactivate(self):
        """
        Deactivate the RegionPicker page. This method calls
        the parent class's deactivate method to finalize
        the page's actions.
        """
        super().deactivate()

    def make_tree(self):
        """
        Create the region tree view with the atlas regions. This method
        populates the region tree with the regions from the atlas,
        setting the region names as the text and the region IDs as the
        item IDs. It also sets the parent structure ID for each region
        to create a hierarchical structure in the tree view.
        """
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
        self.configure_tree_width()

    def configure_tree_width(self):
        """Configure width of region tree display."""

        # Use widget/font metrics to get text width and add
        # padding to account for the checkbox image and indentation.
        tree_font = None
        try:
            tree_font = tk.font.Font(font=self.region_tree.cget('font'))
        except Exception:
            tree_font = tk.font.Font()

        max_width = 0
        for name in self.atlases['names'].index:
            w = tree_font.measure(str(name))
            if w > max_width:
                max_width = w

        # Set the column width
        self.region_tree.column('#0', width=max_width+30, stretch=False)

    def create_widgets(self):
        """
        Create the widgets for this page. This includes:
        - Menu Frame: Contains navigation controls for slides and targets.
        - Slice Frame: Contains the figure to display the target image
        with the selected regions overlaid.
        - Region Frame: Contains the tree view for selecting regions
        of interest (ROIs).
        """
        self.pw = ttk.PanedWindow(
            self, 
            orient=tk.HORIZONTAL, 
            width=800, 
            height=600
        )

        self.main_frame = tk.Frame(self.pw)
        self.region_frame = tk.Frame(self.pw)

        self.menu_frame = tk.Frame(self.main_frame)
        self.slice_frame = tk.Frame(self.main_frame)

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

        self.y_scroll = ttk.Scrollbar(self.region_frame, orient='vertical')
        self.x_scroll = ttk.Scrollbar(self.region_frame, orient='horizontal')
        self.region_tree = self.ModifiedCheckboxTreeView(
            master=self.region_frame,
            yscrollcommand=self.y_scroll.set,
            xscrollcommand=self.x_scroll.set,
            show='tree'
        )
        self.y_scroll['command']=self.region_tree.yview
        self.x_scroll['command']=self.region_tree.xview

        self.region_tree.bind('<Motion>',self.check_update)
        self.region_tree.bind('<ButtonRelease-1>',self.check_update)

    def show_widgets(self):
        """
        Show the widgets on the page. This method packs the
        menu frame, slice frame, and region frame onto the page,
        configures the grid layout, and sets up the navigation
        controls for slides and targets. It also updates the slice
        viewer to display the current target image with the selected
        regions overlaid.
        """
        self.update()
        
        self.pw.pack(expand=True, fill=tk.BOTH)
        self.pw.add(self.main_frame, weight=1)
        self.pw.add(self.region_frame, weight=1)

        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.menu_frame.grid(row=0, column=0, sticky='nsew')
        self.slice_frame.grid(row=1, column=0, sticky='nsew')
        
        self.slide_nav_label.pack(side=tk.LEFT)
        self.slide_nav_combo.pack(side=tk.LEFT)
        
        self.target_nav_combo.pack(side=tk.RIGHT)
        self.target_nav_label.pack(side=tk.RIGHT)

        self.slice_viewer.get_widget().pack(expand=True, fill=tk.BOTH)

        self.region_frame.grid_rowconfigure(0, weight=1)
        self.region_frame.grid_columnconfigure(0, weight=1)
        self.region_tree.grid(row=0, column=0, sticky='nsew')
        self.y_scroll.grid(row=0, column=1, sticky='ns')
        self.x_scroll.grid(row=1, column=0, sticky='ew')

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
        self.curr_target_var.set(1)
        self.update()

    def check_update(self, event=None):
        """
        Check if the selected regions have changed and update the
        segmentation display accordingly. This method retrieves the
        currently checked regions from the region tree, compares them
        with the previously selected regions, and updates the segmentation
        display if there are any changes.
        """
        new_rois = [int(float(s)) for s in self.region_tree.get_checked_no_children()]
        if self.rois != new_rois:
            self.rois = new_rois
            self.show_seg()

    def update(self, event=None):
        """
        Update the figure displaying the segmentation for the current target.
        This method retrieves the current slide and target indices, ensures
        the dropdowns are correctly configured, and displays the segmentation
        for the current target with the selected regions overlaid.
        
        Parameters
        ----------
        event : tk.Event, optional
            The event that triggered the update (default is None).
        """
        self.currSlide = self.slides[self.get_slide_index()]
        self.currTarget = self.currSlide.targets[self.get_target_index()]
        self.target_nav_combo.config(
            values=[i+1 for i in range(self.currSlide.numTargets)]
        )
        self.rois = [int(float(s)) for s in self.region_tree.get_checked_no_children()]
        self.show_seg()

    def show_seg(self):
        """
        Show the current target with the selected regions overlaid.
        This method clears the current axes in the slice viewer, retrieves
        the segmentation image for the current target, and overlays the
        selected regions on the segmentation image. It uses the region colors
        to visualize the selected regions, creating a mask for each checked
        region and displaying them on the segmentation image.
        """
        self.slice_viewer.axes[0].cla()
        seg_img = self.currTarget.get_img()
        seg = self.currTarget.get_seg(verbose=False)
        data_regions = np.zeros_like(seg)

        # create masks for each checked region
        for roi in self.rois:
            mask = self.make_region_mask(self.currTarget, roi) * (roi)
            data_regions += mask
        
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
            
    def make_region_mask(self, target, id):
        """
        Create a mask for the specified region ID and its children. This 
        method generates a binary mask where the pixels corresponding to 
        the specified region ID and the region IDs of its children are 
        set to 1, and all other pixels are set to 0.

        Parameters
        ----------
        target : Target
            The target for which the mask is created.
        id : int
            The ID of the region for which the mask is created.
        
        Returns
        -------
        mask : ndarray
            A binary mask with the same shape as the segmentation image,
            where pixels belonging to the specified region and its children 
            are set to 1.
        """
        seg = target.get_seg(verbose=False)
        mask = (seg==id).astype(np.uint32)
        for child in self.region_tree.get_children(str(float(id))):
            mask += self.make_region_mask(target, int(float(child)))
        return mask

    def on_move(self, event):
        """
        Update the title of the slice viewer with the name of the region
        under the mouse cursor. This method retrieves the pixel coordinates
        from the mouse event, gets the region ID from the segmentation image
        at those coordinates, and updates the title of the slice viewer with
        the name of the region corresponding to that ID. If the mouse is not
        over an axes, it does nothing.
        
        Parameters
        ----------
        event : matplotlib.backend_bases.MouseEvent
            The mouse event containing the x and y coordinates of the mouse cursor.
        """
        if event.inaxes:
            x,y = int(event.xdata), int(event.ydata)
            id = self.currTarget.get_seg(verbose=False)[y,x]
            name = self.get_region_name(id)
            self.slice_viewer.axes[0].set_title(name)
            self.slice_viewer.update()
        
    def on_click(self, event=None):
        """
        Handle mouse click events on the slice viewer. This method checks
        if the mouse click occurred within the axes of the slice viewer, retrieves
        the pixel coordinates from the mouse event, and toggles the checked state
        of the region corresponding to the pixel coordinates in the region tree.
        If the region is already checked, it unchecks it and vice versa. It also
        updates the segmentation display after toggling the checked state.
        
        Parameters
        ----------
        event : matplotlib.backend_bases.MouseEvent, optional
            The mouse event containing the x and y coordinates of the mouse click.
        """
        if event.inaxes:
            x,y = int(event.xdata), int(event.ydata)
            id = float(self.currTarget.get_seg(verbose=False)[y,x])
            if self.region_tree.tag_has("checked", id):
                self.region_tree._uncheck_descendant(id)
                self.region_tree._uncheck_ancestor(id)
            else:
                self.region_tree._check_ancestor(id)
                self.region_tree._check_descendant(id)
            self.update()
            
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
    
    def get_region_name(self, id):
        """
        Get the name of the region corresponding to the specified ID.
        This method retrieves the region DataFrame from the atlases dictionary,
        locates the row with the specified ID, and returns the index (name) of that
        region.

        Parameters
        ----------
        id : int
            The ID of the region for which to get the name.
        
        Returns
        -------
        name : str
            The name of the region corresponding to the specified ID.
        """
        region_df = self.atlases['names']
        return region_df.loc[region_df.id==id].index[0]

    def cancel(self):
        """
        Cancel the actions on the RegionPicker page. This method calls
        the parent class's cancel method to finalize the page's actions.
        """
        for roi in self.rois:
            self.region_tree._uncheck_descendant(float(roi))
            self.region_tree._uncheck_ancestor(float(roi))
        self.rois.clear()
        super().cancel()

    def done(self):
        """
        Finalize the RegionPicker page's actions. This method processes
        the selected regions and saves them in a JSON file. Then, this method
        splits each region into clusters using DBSCAN, creates concave hulls
        for each cluster, and saves the boundaries of these hulls in the target's
        `region_boundaries` attribute. It also assigns wells to each region
        based on the row and column indices, ensuring that wells are spread apart
        """

        with open(os.path.join(self.project.folder, 'regions.json'), 'w') as f:
            json.dump(self.rois, f)

        well = lambda r,c: f"{chr( ord('A') +r )}{c+1}"
        spread = 2 # how far wells should be spread apart
        for slide in self.slides:
            row = 0
            col = 0
            for target in slide.targets:
                target.region_boundaries = {}
                target.wells = {}
                for roi in self.rois:
                    roi_name = self.get_region_name(roi)
                    pts = np.argwhere(self.make_region_mask(target, roi))
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
                            
                            # save well
                            if row >= 8: raise Exception(
                                "Too many ROIs selected, please select less ROIs"
                            )
                            target.wells[shape_name] = well(row, col)
                            col += spread
                            if col >= 12:
                                col %= 12
                                row += spread
        super().done()

    class ModifiedCheckboxTreeView(ttkwidgets.CheckboxTreeview):
        """
        A modified version of the CheckboxTreeview that implements custom
        behavior for checking, unchecking, and tristating items. This class
        extends the `ttkwidgets.CheckboxTreeview` class to provide a tree view
        with checkboxes that can be checked, unchecked, and tristated.

        This class overloads the `_box_click` method to implement custom
        behavior for checking, unchecking, and tristating items based on
        the current state of the checkbox.
        
        It also provides methods to get the checked items and their children,
        as well as a method to get the checked items without their children.
        """

        def __init__(self, master=None, **kw):
            super().__init__(master, **kw)

        def get_checked(self):
            """
            Get the checked items and their children. This method returns
            a list of checked items, including their children, ensuring that
            all descendants of a checked item are also included in the result.
            This method overloads the default behavior to include all checked
            items (parents and children) in the result.
            
            Returns
            -------
            checked : list
                A list of checked items including their children."""
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
        
        def get_checked_no_children(self):
            """
            Get the checked items without their children. This method returns
            a list of checked items, ensuring that no child items of a checked
            item are included in the result.
            
            Returns
            -------
            checked : list
                A list of checked items without their children.
            """
            checked = []
            
            def get_highest_checked_children(item):
                if not self.tag_has("unchecked", item):
                    if self.tag_has("checked", item):
                        checked.append(item)
                    else:
                        for c in self.get_children(item):
                            get_highest_checked_children(c)

            ch = self.get_children("")
            for c in ch:
                get_highest_checked_children(c)
            return checked

        def _box_click(self, event):
            """
            Overload:
            If box is unchecked -> check it 
            If box is checked (and has children) -> make it tristate
            If box is tristate -> make it unchecked
            """
            x, y, widget = event.x, event.y, event.widget
            elem = widget.identify("element", x, y)
            if "image" in elem:
                # a box was clicked
                item = self.identify_row(y)
                if self.tag_has("unchecked", item):
                    self._check_ancestor(item)
                    self._check_descendant(item)
                elif self.tag_has("checked", item) and self.get_children(item):
                    self._tristate_parent(item)
                else:
                    self._uncheck_descendant(item)
                    self._uncheck_ancestor(item)

        def _check_ancestor(self, item):
            """
            Overload:
            Check the box of item and change the state of the boxes of item's
            ancestors accordingly. 
            Modification: parent is always tristate even if all children are
            checked
            """
            self.change_state(item, "checked")
            parent = self.parent(item)
            if parent:
                self._tristate_parent(parent)