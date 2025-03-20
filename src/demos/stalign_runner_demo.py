from demo import Demo
from pages import STalign_Runner

class STalign_RunnerDemo(Demo):

    def __init__(self):
        super().__init__()
        self.load("post_target_processor.pkl")
        self.demo_widget = STalign_Runner(self.widget_frame, self.slides, self.atlases)
        self.checkpoint_name = "post_stalign_runner.pkl"

demo = STalign_RunnerDemo()
demo.run()