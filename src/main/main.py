import tkinter as tk
from tkinter import ttk
from images import Atlas, Slide
from pages import *
from constants import *

class App(tk.Tk):
    def __init__(self):
        # initializes app with main window, navigation bar, prev/next buttons in nav_bar, 
        super().__init__()
        self.create_widgets()
        self.show_widgets()

        self.project = {}
        self.project['slides'] = []
        self.project['atlases'] = {
            FSR: Atlas(),
            DSR: Atlas(),
            FSL: Atlas(),
            DSL: Atlas(),
            'names': None
        }
        self.project['folder'] = None
        self.project['stalign_iterations'] = 0

        # initalize each page with self.main_window as parent
        page_list: tuple[Page] = tuple([
            Starter, 
            SlideProcessor, 
            TargetProcessor,
            STalignRunner,
            VisuAlignRunner,
            RegionPicker,
            Exporter
        ])
        self.pages: list[Page] = [page(self.main_window, self.project) for page in page_list]
        self.page_index = 0
        self.update()
        self.mainloop()

    def create_widgets(self):
        self.main_window = tk.Frame(self)
        self.page_label = ttk.Label(self.main_window)

        self.nav_bar = tk.Frame(self)
        self.prev_btn = ttk.Button(self.nav_bar, command=self.prev_page)
        self.next_btn = ttk.Button(self.nav_bar, command=self.next_page)

    def show_widgets(self):
        # show nav_bar and main_window
        self.main_window.pack(expand=True, fill=tk.BOTH)
        self.page_label.pack()

        self.nav_bar.pack(side=tk.BOTTOM)
        self.prev_btn.pack(side=tk.LEFT)
        self.next_btn.pack(side=tk.RIGHT)
    
    def next_page(self):
        self.pages[self.page_index].done()
        if self.page_index == len(self.pages)-1:
            self.destroy()
            return
        self.page_index += 1
        self.update()

    def prev_page(self):
        self.pages[self.page_index].cancel()
        if self.page_index == 0: 
            self.destroy()
            return
        self.page_index -= 1
        self.update()
    
    def update(self):
        current_page = self.pages[self.page_index]
        
        # activate current page
        current_page.activate()

        # set header label
        self.page_label.config(text=current_page.get_header())

        # logic for showing next and previous buttons
        self.prev_btn.config(text='Previous')
        self.next_btn.config(text='Next')
        if self.page_index == 0:
            self.prev_btn.config(text='Exit')
        
        if self.page_index == len(self.pages)-1:
            self.next_btn.config(text='Finish')


# Actually run the app
app = App()
