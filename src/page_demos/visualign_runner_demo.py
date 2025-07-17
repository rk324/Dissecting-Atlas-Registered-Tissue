from demo import Demo
from pages import VisuAlignRunner

class VisuAlignRunnerDemo(Demo):

    def __init__(self):
        super().__init__()
        self.load("post_stalign_runner.pkl")
        self.createDemoWidget(VisuAlignRunner)
        self.checkpoint_name = "post_visualign_runner.pkl"

demo = VisuAlignRunnerDemo()
demo.run()