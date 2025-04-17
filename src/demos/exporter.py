from demo import Demo
from pages import Exporter

class ExporterDemo(Demo):

    def __init__(self):
        super().__init__()
        self.load("post_region_picker.pkl")
        self.demo_widget = Exporter(self.widget_frame, self.slides, self.atlases)
        self.checkpoint_name = "post_export.pkl"

demo = ExporterDemo()
demo.run()