import sys
import time

from kivy.config import Config
from kivy.event import EventDispatcher
Config.set('graphics', 'resizable', 0)

from kivy.uix.anchorlayout import AnchorLayout
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition

from .skins import SkinsScreen
from client import Client


class ContentManager(App):

    def build_config(self, config):
        config.read('app/contentmanager.ini')

    def build_settings(self, settings):
        # TODO: validate settings
        settings.add_json_panel('Content server settings', self.config, 'app/settings/settings.json')

    def build(self):
        Builder.load_file('app/ui/contentmanager.kv')
        Window.size = (1024, 600)

        c_dispatcher = ConnectedDispatcher()
        main_screen = MainScreen(self.config, name='main_screen')
        c_dispatcher.bind(on_connect=main_screen.on_connect)

        sm = ScreenManager()
        sm.transition = FadeTransition()
        sm.add_widget(LoadingScreen(self.config, c_dispatcher, name='loading_screen'))
        sm.add_widget(main_screen)
        return sm


class ConnectedDispatcher(EventDispatcher):
    def __init__(self, **kwargs):
        self.register_event_type('on_connect')
        super(ConnectedDispatcher, self).__init__(**kwargs)

    def send_connected_ev(self):
        self.dispatch('on_connect')

    def on_connect(self):
        # add debug log here
        pass


class LoadingScreen(Screen):

    def __init__(self, config, dispatcher, **kwargs):
        super(LoadingScreen, self).__init__(**kwargs)
        self.dispatcher = dispatcher
        self.config = config
        self.connected = False
        self.text_loader = self.ids.text_loader
        self.ac_addr = self.config.get('ac', 'address')
        if self.ac_addr is None or self.ac_addr == "":
            self.text_loader.text = "Invalid skins server address or is empty"
            Clock.schedule_once(self.handle_err, 2)
        else:
            self.text_loader.text = "Trying to connect to " + self.config.get('ac', 'address') + "..."
            Clock.schedule_once(self.test_connection, 2)

    def test_connection(self, dt):
        try:
            client = Client(self.ac_addr)
            client.ping()
            self.text_loader.text = "Connected to " + self.config.get('ac', 'address') + "..."
            self.connected = True
        except Exception as exc:
            print(exc)
            self.text_loader.text = "Unable to connect to " + self.config.get('ac', 'address') + "... Exiting!"
        Clock.schedule_once(self.handle_err, 2)

    def handle_err(self, dt):
        if not self.connected:
            sys.exit(1)
        self.dispatcher.send_connected_ev()


class MainScreen(Screen):

    def __init__(self, config, **kwargs):
        # add Menu and Content widgets
        # Content widgets contains screens for ACC and AC
        super(MainScreen, self).__init__(**kwargs)
        self.config = config

    def on_connect(self, obj):
        screen = self.manager.get_screen('main_screen')
        self.manager.switch_to(screen)
        self.add_widget(SkinsScreen(self.config))
