from demo import Demo
from pages import SlideProcessor

class SlideProcessorDemo(Demo):

    def __init__(self):
        super().__init__()
        self.load("post_starter.pkl")
        self.createDemoWidget(SlideProcessor)
        self.checkpoint_name = "post_slide_processor.pkl"

demo = SlideProcessorDemo()
demo.run()