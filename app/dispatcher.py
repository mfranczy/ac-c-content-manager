from kivy.event import EventDispatcher


class CustomDispatcher(EventDispatcher):
    def __init__(self, **kwargs):
        self.register_event_type('on_initialize')
        super(CustomDispatcher, self).__init__(**kwargs)

    def do_initialize(self, *args):
        self.dispatch('on_initialize')

    def on_initialize(self):
        # add debug log here
        pass
