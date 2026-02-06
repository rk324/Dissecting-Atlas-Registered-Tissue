import nibabel as nib
import numpy as np
import os
import pandas as pd
import skimage as ski
import tkinter as tk
from tkinter import ttk

from dart.pages.base import BasePage
from dart.utils import get_target_name

class VisuAlignRunner(BasePage):
    """
    Page for running VisuAlign. This page prepares the data
    for VisuAlign, including creating a NIfTI file with the
    segmentation stack and a JSON file with the necessary
    information for VisuAlign. It also provides instructions
    for the user to follow in order to perform the alignment
    in VisuAlign and save the results.
    """
    def __init__(self, master, project):
        super().__init__(master, project)
        self.header = "Running VisuAlign."

    def activate(self):
        """
        Activate the VisuAlignRunner page. This method prepares
        the data for VisuAlign by creating a NIfTI file with the
        segmentation stack and a JSON file with the necessary
        information for VisuAlign. It also creates the necessary
        folders and files for exporting the results.
        """
        # stack latest seg of all targets and pad as necessary to create 3 dimensions np.array
        raw_stack = [target.get_seg() for slide in self.slides for target in slide.targets]
        shapes = np.array([seg.shape for seg in raw_stack])
        max_dims = [shapes[:,0].max(), shapes[:,1].max()]
        paddings = max_dims-shapes
        stack = np.array([np.pad(r, ((p[0],0),(0,p[1]))) for p,r in zip(paddings, raw_stack)])
        stack = np.transpose(np.flip(stack, axis=(0,1)), (-1,0,1))
        nifti = nib.Nifti1Image(stack, np.eye(4)) # create nifti obj
        
        self.visualign_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..',
            'VisuAlign-v0_9'
        )
        self.custom_atlas_path = os.path.join(
            self.visualign_path,
            'custom_atlas.cutlas',
            'labels.nii.gz'
        )
        
        nib.save(nifti, self.custom_atlas_path)

        visualign_export_folder = os.path.join(self.project.folder,'EXPORT_VISUALIGN_HERE')
        if not os.path.exists(visualign_export_folder):
            os.mkdir(visualign_export_folder)

        with open(os.path.join(self.project.folder,'CLICK_ME.json'),'w') as f:
            f.write('{')
            f.write('"name":"", ')
            f.write('"target":"custom_atlas.cutlas", ')
            f.write('"aligner": "prerelease_1.0.0", ')
            f.write('"slices": [')
            i=0
            for sn,slide in enumerate(self.slides):
                for ti,t in enumerate(slide.targets):
                    filename = get_target_name(sn, ti)+'.png'
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
        """
        Deactivate the VisuAlignRunner page. This method
        deletes the JSON file for interfacing with VisuAlign
        along with the segmentation stack. 
        """
        os.remove(os.path.join(self.project.folder,'CLICK_ME.json'))
        os.remove(self.custom_atlas_path)
        super().deactivate()

    def create_widgets(self):
        """
        Create the widgets for this page. This includes:
        - Run Button: A button to open VisuAlign and start the alignment process.
        - Instructions Label: A label with instructions for the user to follow
        """
        self.run_btn = ttk.Button(
            master=self,
            text="Open VisuAlign",
            command=self.run
        )

        self.instructions_label = ttk.Label(
            master=self,
            text="Instructions:\n" \
                 "1. Click \"Open VisuAlign\" button\n" \
                 "2. Click File > Open > \"CLICK_ME.json\"\n" \
                 "3. Adjust alignment with VisuAlign until satisfied\n" \
                 "4. Click File > Export > \"EXPORT_VISUALIGN_HERE\"\n" \
                 "5. Close VisuAlign after notification of successful saving " \
                 "of segmentation.\n"
                 "Note: The \"CLICK_ME.json\" file and the " \
                 "\"EXPORT_VISUALIGN_HERE\" folder are both located within " \
                 "the current project folder.\n" \
        )

    def show_widgets(self):
        """
        Show the widgets on the page. This method packs the
        run button and instructions label onto the page.
        """
        self.instructions_label.pack()
        self.run_btn.pack()

    def run(self):
        """
        Run the VisuAlign application. This method changes the
        current working directory to the VisuAlign directory and
        executes the command to run VisuAlign using the Java executable.
        After VisuAlign has been run, it calls `load_results`
        to load the results from the exported files.
        """
        print("running visualign")
        cmd = rf"cd {self.visualign_path} && {os.path.join('bin','java.exe')} --module qnonlin/visualign.QNonLin"
        os.system(cmd)
        self.load_results()
    
    def load_result_filename(self, filename):
        """
        Load the results from a specified filename. This method checks if the
        exported files from VisuAlign exist, and if so, it processes the results
        to extract the segmentation and outlines. If the files do not exist,
        it raises an exception indicating that the user needs to run VisuAlign first.
        
        Parameters
        ----------
        filename : str
            The filename of the exported results from VisuAlign.

        Returns
        -------
        seg : np.ndarray
            A numpy array representing the segmentation mask of the Target image.
        """
        
        nutil_json_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..',
            'resources',
            'Rainbow 2017.json'
        )
        regions_nutil = pd.read_json(nutil_json_path)
        with open(filename, 'rb') as fp:
            buffer = fp.read()
        shape = np.frombuffer(buffer, dtype=np.dtype('>i4'), offset=1, count=2) 
        data = np.frombuffer(buffer, dtype=np.dtype('>i2'), offset=9)
        
        data = data.reshape(shape[::-1])
        data = data[:-1,:-1]
        
        names = regions_nutil['name'].to_numpy()[data] 
        seg = names.copy()
        for region_name in np.unique(names):
            mask = names==region_name
            seg[mask] = self.atlases['names'].id[region_name]
        
        return seg.astype(np.uint32)

    def load_results(self):
        """
        Load the results from VisuAlign. This method processes
        the results to extract the segmentation and outlines and
        saves them.
        """
        
        for sn,slide in enumerate(self.slides):
            for ti,t in enumerate(slide.targets):
                visualign_nl_flat_filename = os.path.join(
                    self.project.folder,
                    "EXPORT_VISUALIGN_HERE",
                    get_target_name(sn,ti)+"_nl.flat"
                )
                
                print(f'we are looking for {visualign_nl_flat_filename}')
                
                try:
                    t.seg['visualign'] = self.load_result_filename(visualign_nl_flat_filename)
                except:
                    tk.messagebox.showwarning(
                        title="VisuAlign results not found",
                        message="You may have closed VisuAlign without "
                                "exporting the results. If this was "
                                "unintentional, please click \"Run\" again and "
                                "redo your manual adjustments . Remember to "
                                "export your results by clicking:\n "
                                "File > Export > \"EXPORT_VISUALIGN_HERE\" "
                    )
                    return

                # save segmentation
                self.save_results(sn, ti)

    def save_results(self, slideIndex, targetIndex):
        """
        Save the results from VisuAlign for a specific slide and target.
        This method processes the results to extract the segmentation and
        outlines, and saves them in the respective target folder.

        Parameters
        ----------
        slideIndex : int
            The index of the slide for which to save the results.
        targetIndex : int
            The index of the target for which to save the results.
        """
        folder_path = os.path.join(
            self.project.folder, 
            get_target_name(
                slideIndex, 
                targetIndex
            )
        )
        target = self.slides[slideIndex].targets[targetIndex]

        # save segmentation
        target.save_seg(folder_path, 'visualign')
        print(f"saved visualign results for slide #{slideIndex}, target #{targetIndex}")

    def done(self):
        """
        Finalize the VisuAlignRunner page's actions. This method
        calls the parent class's done method.
        """

        super().done()
    
    def cancel(self):
        """
        Cancel the actions on the VisuAlignRunner page. This method
        clears the VisuAlign segmentation for each target, effectively
        resetting the manual alignment results.
        """
        for slide in self.slides:
            for target in slide.targets:
                if 'visualign' in target.seg:
                    target.seg.pop('visualign')

        super().cancel()