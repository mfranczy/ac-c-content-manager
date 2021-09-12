from kivy.config import Config
Config.set('graphics', 'width', '1024')
Config.set('graphics', 'height', '768')

from kivymd.app import MDApp
from .screens import MainScreen
from .dispatcher import CustomDispatcher


class App(MDApp):
    
    def __init__(self, *args, **kwargs):
        self.custom_dispatcher = CustomDispatcher()
        super(App, self).__init__(*args, **kwargs)

    def build_config(self, config):
        # TODO: check multiple locations
        # TODO: handle not found error
        config.read('app/config.ini')

    def build_settings(self, settings):
        # TODO: validate settings
        settings.add_json_panel('Content server settings', self.config, 'app/settings/settings.json')
    
    def build(self):
        self.title = "simrace.pl - build v0.0.1-alpha"
        self.icon = "icon.ico"
        return MainScreen()
