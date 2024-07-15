import tkinter as tk
from Image import Image
from Atlas import Atlas

root = tk.Tk()
img = Atlas(root)
img.frame.pack(side=tk.LEFT)
img2 = Image(root)
img2.frame.pack(side=tk.LEFT)

root.mainloop()
