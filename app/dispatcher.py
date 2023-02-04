from kivy.event import EventDispatcher


class CustomDispatcher(EventDispatcher):
    def __init__(self, **kwargs):
        self.register_events()
        super(CustomDispatcher, self).__init__(**kwargs)

    def register_events(self):
        self.register_event_type('on_initialize')
        self.register_event_type('on_refresh')
        self.register_event_type('on_recreate_all')
        self.register_event_type('on_download_all')
        self.register_event_type('on_activate_league')
        self.register_event_type('on_open_backup')
        self.register_event_type('on_open_zip_skin')

    def do_initialize(self, *args):
        self.dispatch('on_initialize')

    def do_refresh(self, *args):
        self.dispatch('on_refresh')

    def do_recreate_all(self, *args):
        self.dispatch('on_recreate_all')

    def do_download_all(self, *args):
        self.dispatch('on_download_all')

    def do_activate_league(self, *args):
        self.dispatch('on_activate_league')

    def do_open_backup(self, *args):
        self.dispatch('on_open_backup')

    def do_open_zip_skin(self, *args):
        self.dispatch('on_open_zip_skin')

    def on_initialize(self):
        # add debug log here
        pass

    def on_refresh(self):
        # add debug log here
        pass

    def on_recreate_all(self):
        # add debug log here
        pass

    def on_download_all(self):
        # add debug log here
        pass

    def on_activate_league(self):
        # add debug log here
        pass

    def on_open_backup(self):
        # add debug log here
        pass

    def on_open_zip_skin(self):
        # add debug log here
        pass
