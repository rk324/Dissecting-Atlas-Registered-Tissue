from demo import Demo
from pages import VisuAlignRunner

class VisuAlignRunnerDemo(Demo):

    def __init__(self):
        super().__init__()
        self.load("post_stalign_runner.pkl")
        self.demo_widget = VisuAlignRunner(self.widget_frame, self.slides, self.atlases)
        self.checkpoint_name = "post_visualign_runner.pkl"

demo = VisuAlignRunnerDemo()
demo.run()