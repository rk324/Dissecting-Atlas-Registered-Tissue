from demo import Demo
from pages import RegionPicker

class RegionPickerDemo(Demo):

    def __init__(self):
        super().__init__()
        self.load("post_visualign_runner.pkl")
        self.createDemoWidget(RegionPicker)
        self.checkpoint_name = "post_region_picker.pkl"

demo = RegionPickerDemo()
demo.run()