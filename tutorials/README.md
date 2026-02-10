# User Guide

## Installation

See the [Installation Guide](https://github.com/kebschulllab/Dissecting-Atlas-Registered-Tissue/tree/main?tab=readme-ov-file#installation) on the main README for instructions on installing `DART`.

## Getting Started

Prior to using `DART`, calibration points must be added to the slide. Although natural landmarks on the sample can be used, we recommend creating artificial calibration points that can be reliably located. To do this, use the laser to mark cross-shaped fiducials in the slide membrane at the top left, top right, and bottom right corners of the slide (**Figure 1**). Then, take an overview image of the whole slide, including fiducial crosses, to use in `DART`.

![Cross Fiducial Example](assets/calibration_points.png)  
**Figure 1. Cross Fiducial Example**

## Load the Data
On the `DART` starter page (**Figure 2**), select a segmentation method and atlases if using DART's in-built segmentation algorithm. Also, select the sample images by clicking **Browse** and selecting the folder containing the images. `DART` will load each image in the folder as a separate slide and create a subfolder to store results and intermediate files. The name of the subfolder will follow the format `DART-[datetime]`.

![Starter Page](assets/starter.png)  
**Figure 2. Starter Page**

### Selecting a Segmentation Method
`DART` has an in-built segmentation algorithm that implements slice to atlas registration using [STalign](https://github.com/JEFworks-Lab/STalign). To use this algorithm, select "DART in-built" in the Segmentation Method dropdown. Alternatively, users may use their own segmentation pipelines by selecting "Other".

### Selecting an Atlas
Currently, `DART` has 5 atlas options available from varying resolutions and imaging workups. Atlases comprise three components: a reference atlas that contains the spatial cell density of the organ of interest, a labels atlas that maps each voxel from the reference atlas to an ID corresponding to a specific region in the tissue, and a table containing information about the regions and their hierarchical structure.

## Mark Calibration Points and Select Sections

On the slide processing page (**Figure 3**), the **Add Calibration Points** tab is selected by default. Annotate the calibration points (marked earlier with the LMD) by clicking on the calbration point and then selecting **Add Point** on the top panel. Next, switch to the **Select Slices** tab on the top panel and drag a box around each section to delineate the individual sections. Since multiple sections can be mounted on a single slide, this allows for bulk processing of several sections on each slide. When annotating images in this software, a common color scheme is used. Red annotations have not been saved, green annotations have been saved, and orange annotations have been recently saved and can be removed with a corresponding button at the top of the page. This color scheme is also applied when annotating calibration points, and it continues throughout the software.

![Slide Processing Page](assets/slide_processor.png)  
**Figure 3. Slide Processing Page**

## Alignment and Segmentation

The following page(s) will depend on your selection of segmentation method from the Starter Page. See the [Segmentation Guide](https://github.com/kebschulllab/Dissecting-Atlas-Registered-Tissue/blob/main/tutorials/SEGMENTATION.md) for more details. If you selected "DART in-built" you will complete two pages that guide you through a semi-automatic registration to the atlat you chose. If you opted to upload your own segmentation, our guide has a section with instructions on doing so. After generating a segmentation, whether through our in-built algorithm or through your own custom pipelines, we provide the option to manually adjust the segmentation in VisuAlign.

## Adjust Segmentation

In the VisuAlign Runner page (**Figure 8**), make manual adjustments to the segmentation using VisuAlign (**Figure 9**). This enables greater control over the region boundaries. Since VisuAlign is a separate software, `DART` opens it through the command terminal, when you click **Open VisuAlign**. 

You will find the `CLICK ME` file in the `DART-[datetime]` subfolder with your section images. You can do this by hitting the space bar while hovering your mouse on a region you wish to move. This will make a cross appear at the pointer location. You can then click and drag the cross around to adjust the local alignment. If you have multiple slices, you can navigate slices with the arrows in the top right corner.  After adjusting the alignment, export the alignment to the EXPORT_VISUALIGN_HERE folder, and close VisuAlign.

![VisuAlign Runner Page](assets/visualign_runner.png)  
**Figure 8. VisuAlign Runner Page**

![VisuAlign](assets/visualign.png)  
**Figure 9. VisuAlign**

## Select ROIs

In the region selection page (**Figure 10**), select the regions of interest (ROIs). This can be done by either clicking on the ROIs in the image or by navigating to and toggling the checkbox of the region in the tree view. Each has three possible states: unchecked, checked (marked by a check mark), and tristate (marked by a filled box). Unchecked regions will not be exported for dissection. Checked regions and all their child regions are stitched together for combined dissection. Tristate regions are the ancestors of checked regions that are exported and dissected separately. This distinction between checked and tristate regions allows dissection of fine and broad groups of regions. For example you could define and dissect the entire cerebral cortex by using a checked box for parent **Cerebral Cortex** and all child regions. Or, you could use a filled box (tristate) for parent **Cerebral cortex**, and all immediate child regions (i.e. Visual Cortex, Somatosensory cortex, etc) that are checked are exported and dissected separately.

![Region Selection Page](assets/region_picker.png)  
**Figure 10. Region Selection Page**

## Export ROI Boundaries

The export page (**Figure 11**) allows the user to select sections for export. All the sections of a slide can be exported together in one batch file for the slide, or individual sections can be exported. This allows the user to group their LMD cutting jobs as desired. The `.xml` files necessary for LMD dissection are in the `DART-[datetime]` subfolder, under the subfolder `output`.

![Export Page](assets/exporter.png)  
**Figure 11. Export Page**

## Import to LMD

Before importing shapes onto the LMD, switch the LMD to the desired objective for cutting. For example, if the user wants to cut their shapes using the 10x objective, then they must first switch to that objective. Then, click File > Import Shapes and select the `.xml` file containing the shape(s) to be imported. This will trigger a series of prompts to select shapes and calibrate the LMD. Navigate through these prompts until the final prompt, “Use the actual magnification for all imported shapes?”, is reached. Click “Yes”. 

The shapes list should populate with the imported shapes. Select a shape to view it overlaid on the section, and click “Start cut” to initiate the laser dissection process for this shape. Alternatively, all the shapes may be selected and dissected. Note that `DART` automatically assigns wells to each shape, spaced out with one well in between. These well assignments may be adjusted in the Leica LMD software.
