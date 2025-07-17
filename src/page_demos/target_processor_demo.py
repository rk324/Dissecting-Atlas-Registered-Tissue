from demo import Demo
from pages import TargetProcessor

class TargetProcessorDemo(Demo):

    def __init__(self):
        super().__init__()
        self.load("post_slide_processor.pkl")
        self.createDemoWidget(TargetProcessor)
        self.checkpoint_name = "post_target_processor.pkl"

demo = TargetProcessorDemo()
demo.run()