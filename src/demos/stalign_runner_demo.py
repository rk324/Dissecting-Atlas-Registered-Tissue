from demo import Demo
from pages import STalignRunner

class STalignRunnerDemo(Demo):

    def __init__(self):
        super().__init__()
        self.load("post_target_processor.pkl")
        self.createDemoWidget(STalignRunner)
        self.checkpoint_name = "post_stalign_runner.pkl"

demo = STalignRunnerDemo()
demo.run()