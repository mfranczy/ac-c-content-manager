from kivy.config import Config
Config.set('graphics', 'resizable', 0)

from kivy.lang import Builder
from kivy.app import App
from kivy.core.window import Window

from .skins import SkinsView


class ContentManager(App):

    def build_config(self, config):
        config.read('app/contentmanager.ini')

    def build_settings(self, settings):
        # TODO: validate settings
        settings.add_json_panel('Content server settings', self.config, 'app/settings/settings.json')

    def build(self):
        Builder.load_file('app/ui/contentmanager.kv')
        Window.size = (1024, 600)
        return SkinsView(self.config)
