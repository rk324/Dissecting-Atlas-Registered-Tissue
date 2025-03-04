from demo import Demo
from pages import SlideProcessor

class SlideProcessorDemo(Demo):

    def __init__(self):
        super().__init__()
        self.load("post_starter.pkl")
        self.demo_widget = SlideProcessor(self.widget_frame, self.slides, self.atlases)
        self.checkpoint_name = "post_slide_processor.pkl"


demo = SlideProcessorDemo()
demo.run()
'''
starter = Starter(root, slides, atlases)
starter.load_atlas_info(os.path.join('atlases','allen_nissl_100um'))
starter.load_slides('demo_images')
demo = SlideProcessor(root, slides, atlases)
demo.activate()
root.mainloop()'''