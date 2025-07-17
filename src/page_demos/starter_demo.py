from demo import Demo
from pages import Starter

class StarterDemo(Demo):

    def __init__(self):
        super().__init__()
        self.createDemoWidget(Starter)
        self.checkpoint_name = "post_starter.pkl"


demo = StarterDemo()
demo.run()