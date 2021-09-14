from kivymd.uix.screen import MDScreen
from kivymd.app import MDApp
from kivy.clock import Clock
from kivy.uix.screenmanager import ScreenManager, FadeTransition

from .widgets import MenuWidget, SkinWidget
from .clients import FTPClient


class MainScreen(ScreenManager):

    def __init__(self, *args, **kwargs):
        self.app = MDApp.get_running_app()
        self.ftp = FTPClient()
        super(MainScreen, self).__init__(*args, **kwargs)
        self.transition = FadeTransition()

        self._register_screens()
        self.app.custom_dispatcher.bind(on_refresh=self.on_refresh)

    def on_refresh(self, *args):
        self.content.ids['ac_skins'].clear_widgets()
        self.content.ids['acc_skins'].clear_widgets()
        self.remove_widget(self.loader)
        self.remove_widget(self.content)
        self.add_widget(self.loader)
        self.add_widget(self.content)

    def _register_screens(self):
        self.loader = LoaderScreen(name='loader')
        self.content = ContentScreen(name='content')

        self.app.custom_dispatcher.bind(on_initialize=self.content.on_initialize)

        self.add_widget(self.loader)
        self.add_widget(self.content)

class LoaderScreen(MDScreen):

    def __init__(self, *args, **kwargs):
        super(LoaderScreen, self).__init__(*args, **kwargs)
        self.loader_label = self.ids.loader_label

    def on_enter(self):
        Clock.schedule_once(self.load)

    def switch_screen(self):
        self.manager.current = self.name

    def on_leave(self):
        self.loader_label.text = "Loading..."

    def load(self, *args):
        self.loader_label.text = "Trying to connect to: {}...".format(self.manager.ftp.server)
        try:
            self.manager.ftp.ping()
        except Exception as exc:
            self.loader_label.text = "Unable to connect to: {}\n{}\n\nCheck your config by pressing F1 and retry.".format(self.manager.ftp.server, exc)
        else:
            self.loader_label.text = "Successfully connected to: {}...".format(self.manager.ftp.server)
            Clock.schedule_once(self.initialize_content)

    def initialize_content(self, *args):
        self.loader_label.text += "\n\nInitializing content..."
        self.manager.app.custom_dispatcher.do_initialize()


class ContentScreen(MDScreen):
    
    def __init__(self, *args, **kwargs):
        self.menu = MenuWidget()
        super(ContentScreen, self).__init__(*args, **kwargs)

    def on_initialize(self, obj):        
        self.initialize_ac_skins()
        self.initialize_acc_skins()
        self.switch_screen()

    def switch_screen(self):
        self.manager.current = self.name

    def initialize_ac_skins(self):
        skins = self.manager.ftp.list_skins("ac")
        for skin in skins:
            # TODO: fix duplicated skins from different ids
            self.ids.ac_skins.add_widget(SkinWidget(remote_skin_path=skin[0], remote_timestamp=skin[1], skin_type="ac"))

    def initialize_acc_skins(self):
        skins = self.manager.ftp.list_skins("acc")
        for skin in skins:
            # TODO: fix duplicated skins from different ids
            self.ids.acc_skins.add_widget(SkinWidget(remote_skin_path=skin[0], remote_timestamp=skin[1], skin_type="acc"))


class SettingsScreen(MDScreen):

    __config__ = ('generic_user', 'generic_server', 'ac_skins_dir', 'acc_skins_dir')

    def __init__(self, *args, **kwargs):
        super(SettingsScreen, self).__init__(*args, **kwargs)
        self.app = MDApp.get_running_app()
        self.config = self.app.config
        self.set_current_settings()


    def set_current_settings(self):
        for attr in self.__config__:
            if not self.ids.get(attr, False):
                continue
            obj = self.ids[attr]
            setattr(self, attr, obj)
            try:
                section, name = attr.split("_", 1)
                obj.text = self.config.get(section, name)
            except Exception as exc:
                print(exc)

    def confirm(self, *args, **kwargs):
        for attr in self.__config__:
            try:
                obj = getattr(self, attr)
                section, name = attr.split("_", 1)
                self.config.set(section, name, obj.text)
            except Exception as exc:
                print(exc)
        self.config.write()
        self.app.close_settings()
        self.app.custom_dispatcher.do_refresh()
