import tkinter as tk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,  
NavigationToolbar2Tk) 
import skimage as ski

'''
Abstract Image class for displaying atlas and target images
will have child classes: atlas, target

### fields ###
__frame: the frame containing image and possible other 
features (see child classes)

__img: img data

load_file_btn: button for loading image data, is hidden 
after image chosen

### functions ###
__init__: creates frame to hold everything, load & display image
if filename provided

display: displays image dat

load: loads image data from file selected via file dialog
'''
class Image: 

    '''
    Initialize with master frame and optional filename of image.
    Create button to load image data
    Will load and display image and if filename is provided
    '''
    def __init__(self, master, filename=None):
        self.__frame = tk.Frame(master=master)
        self.__frame.pack()

        self.load_file_btn = tk.Button(master=self.__frame, text="Load data", command=self.load)
        self.load_file_btn.pack()
        
        if filename is not None: self.load(filename)
        
    '''
    Load image data using a file dialog, then call display()
    if file is chosen and hide file load button.
    Takes optional filename parameter.
    Returns True if successful image load, false is no valid image file chosen.
    '''
    def load(self, filename=None):
        
        if filename is None:
            file = tk.filedialog.askopenfile() # TODO: make it only allow image files, handle errors by bad file load
            if file is None:
                return False
            filename = file.name
        
        self.__img = ski.io.imread(filename)
        self.load_file_btn.pack_forget()
        self.display()

        return True
  
    '''
    Display image data using matplotlib
    '''
    def display(self):
        fig = Figure()
        fig.add_subplot(111).imshow(self.__img)
        canvas = FigureCanvasTkAgg(fig,master=self.__frame)
        canvas.draw()
        
        # add mpl toolbar to allow zoom, translation
        toolbar = NavigationToolbar2Tk(canvas, self.__frame) 
        toolbar.update() 

        canvas.get_tk_widget().pack()
    
        
