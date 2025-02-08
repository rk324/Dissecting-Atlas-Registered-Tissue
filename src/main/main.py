import tkinter as tk
from tkinter import ttk
import os
from images import Atlas, Slide
#from Atlas import Atlas
from Pages import *

class App(tk.Tk):
    def __init__(self):
        # initializes app with main window, navigation bar, prev/next buttons in nav_bar, 
        super().__init__()
        self.create_widgets()
        self.show_widgets()

        # TODO: template Slide class, adjust Atlas class

        self.slides: list[Slide] = []
        self.ref_atlas = {"full size": Atlas(), "downscaled": Atlas()}
        self.label_atlas = {"full size": Atlas(), "downscaled": Atlas()}

        page_list: tuple[Page] = (Starter,STalign_Prep)
        self.pages: list[Page] = [page(self.main_window, self.slides, self.ref_atlas, self.label_atlas) for page in page_list] # initalize each page in here with self.main_window as parent
        self.page_index = 0

        self.mainloop()


    def create_widgets(self):
        self.main_window = tk.Frame(self)
        self.nav_bar = tk.Frame(self)
        self.prev_btn = ttk.Button(self.nav_bar, command=self.prev_page)
        self.next_btn = ttk.Button(self.nav_bar, command=self.next_page)

    def show_widgets(self):
        # show nav_bar and main_window
        self.main_window.grid(row=1, column=0, sticky='we')
        self.nav_bar.grid(row=2, column=0,sticky='se', padx=10, pady=5)
        self.prev_btn.pack(side=tk.LEFT)
        self.next_btn.pack(side=tk.RIGHT)
    
    def next_page(self):
        if self.page_index == len(self.pages)-1:
            self.destroy()
            return

        self.pages[self.page_index].deactive()
        self.page_index += 1
        self.update()

    def prev_page(self):

        if self.page_index == 0: 
            self.destroy()
            return
        
        self.pages[self.page_index].deactive()
        self.page_index -= 1
        self.update()
    
    def update(self):
        # activate current page
        #self.pages[self.page_index].activate()

        # logic for showing next and previous buttons
        self.prev_btn.config(text='Previous')
        self.next_btn.config(text='Next')
        if self.page_index == 0:
            self.prev_btn.config(text='Exit')
        elif self.page_index == len(self.pages)-1:
            self.next_btn.config(text='Finish')


# Actually run the app
app = App()
#app.start()
