from kivymd.uix.screen import MDScreen
from kivymd.app import MDApp
from kivy.clock import Clock
from kivy.uix.screenmanager import ScreenManager, FadeTransition

from .widgets import MenuWidget, SkinWidget
from .clients import HTTPClient


class MainScreen(ScreenManager):

    def __init__(self, *args, **kwargs):
        self.app = MDApp.get_running_app()
        self.http_client = HTTPClient()
        super(MainScreen, self).__init__(*args, **kwargs)
        self.transition = FadeTransition()

        self._register_screens()
        self.app.custom_dispatcher.bind(on_refresh=self.on_refresh)

    def on_refresh(self, *args):
        self.loader.switch_screen()

    def _register_screens(self):
        self.loader = LoaderScreen(name='loader')
        self.content = ContentScreen(name='content')

        self.app.custom_dispatcher.bind(on_initialize=self.content.on_initialize)

        self.add_widget(self.loader)
        self.add_widget(self.content)

class LoaderScreen(MDScreen):

    def __init__(self, *args, **kwargs):
        self.menu = MenuWidget(disabled_items=['download_all', 'recreate_all'])
        super(LoaderScreen, self).__init__(*args, **kwargs)
        self.loader_label = self.ids.loader_label

    def on_enter(self):
        Clock.schedule_once(self.load)

    def switch_screen(self):
        if self.manager.current != self.name:
            self.manager.current = self.name
        else:
            self.on_enter()

    def on_leave(self):
        self.loader_label.text = "Loading..."

    def load(self, *args):
        self.loader_label.text = "Trying to connect to: {}...".format(self.manager.http_client.server)
        try:
            self.manager.http_client.ping()
        except Exception as exc:
            self.loader_label.text = "Unable to connect to: {}\n{}\n\nCheck your config by pressing F1 and retry.".format(self.manager.http_client.server, exc)
        else:
            self.loader_label.text = "Successfully connected to: {}...".format(self.manager.http_client.server)
            Clock.schedule_once(self.initialize_content)

    def initialize_content(self, *args):
        self.loader_label.text += "\n\nInitializing content..."
        self.manager.app.custom_dispatcher.do_initialize()


class ContentScreen(MDScreen):

    _ACC_ID = 1
    _AC_ID = 2

    def __init__(self, *args, **kwargs):
        self.menu = MenuWidget()
        self.skins = {}
        super(ContentScreen, self).__init__(*args, **kwargs)

    def on_initialize(self, obj):
        for skin in self.manager.http_client.list_skins():
            skin_id = "{}_{}_{}_{}".format(skin["game_id"], skin["league_id"], skin["car_name"], skin["skin_name"])
            
            game_id = int(skin['game_id'])
            skin_type = ""
            if game_id == self._ACC_ID:
                skin_type = 'acc'
            elif game_id == self._AC_ID:
                skin_type = 'ac'
            else:
                continue  

            if self.skins.get(skin_id):
                if self.skins[skin_id].sum_control != skin['sum']:
                    self.skins[skin_id].refresh_required = True
                    self.skins[skin_id].sum_control = skin['sum']
            else:
                widget = SkinWidget(skin, skin_type)
                self.skins[skin_id] = widget
                if game_id == self._ACC_ID:   
                    self.ids.acc_skins.add_widget(widget)
                elif game_id == self._AC_ID:
                    self.ids.ac_skins.add_widget(widget)

        self.switch_screen()

    def switch_screen(self):
        self.manager.current = self.name


class SettingsScreen(MDScreen):

    __config__ = ('generic_user', 'generic_password', 'generic_server', 'ac_skins_dir', 'acc_skins_dir')

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
