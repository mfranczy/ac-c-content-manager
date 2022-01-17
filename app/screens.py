import os
import shutil

from functools import partial
from zipfile import ZipFile

from kivymd.uix.screen import MDScreen
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from kivymd.app import MDApp
from kivy.clock import Clock
from kivy.uix.screenmanager import ScreenManager, FadeTransition,\
    ScreenManagerException
from kivymd.uix.snackbar import Snackbar
from kivy.utils import get_color_from_hex

from .widgets import MenuWidget, SkinWidget, LeagueButtonWidget
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
        for screen in self.content.ids.content_manager.screens:
            # TODO: very hacky - fix me
            screen.children[0].children[0].children[0].clear_widgets()
        self.loader.switch_screen()

    def _register_screens(self):
        self.loader = LoaderScreen(name='loader')
        self.content = ContentScreen(name='content')
        self.backup = BackupScreen(name='backup')
        self.backup.create_backup(skip_dialog=True)

        self.app.custom_dispatcher.bind(on_initialize=self.content.on_initialize)

        self.add_widget(self.loader)
        self.add_widget(self.content)
        self.add_widget(self.backup)


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
        self.league_skins = {}
        self.skins = {}
        super(ContentScreen, self).__init__(*args, **kwargs)

    def on_initialize(self, obj):
        left_skins = list(self.skins.keys())
        active = True
        for skin in self.manager.http_client.list_skins():
            league_id = "league_" + str(skin['league_id'])
            if not league_id in self.league_skins:
                self.manager.content.ids.leagues_buttons.add_widget(
                    LeagueButtonWidget(league_id, skin['league_name'], active)
                )
                active = False
                self.manager.content.ids.content_manager.add_widget(
                    SkinScreen(league_id)
                )
                self.league_skins[league_id] = True

            try:
                screen = self.manager.content.ids.content_manager.get_screen(league_id)
            except ScreenManagerException:
                # TODO: log errors here
                continue
            
            # TODO: very hacky - fix me
            list_view = screen.children[0].children[0].children[0]

            skin_id = "{}_{}_{}_{}".format(skin["game_id"], skin["league_id"], skin["car_name"], skin["skin_name"])
            if skin_id in left_skins:
                left_skins.remove(skin_id)

            game_id = int(skin['game_id'])
            skin_type = ""
            if game_id == self._ACC_ID:
                skin_type = 'acc'
            elif game_id == self._AC_ID:
                skin_type = 'ac'
            else:
                continue

            widget = self.skins.get(skin_id)
            if widget is None:
                widget = SkinWidget(skin, skin_type)
                self.skins[skin_id] = widget
            else:
                widget.remote_timestamp = skin['timestamp']
            list_view.add_widget(widget)

        for skin in left_skins:
            widget = self.skins.pop(skin)
            widget.unregister_events()
            del widget

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


class BackupScreen(MDScreen):

    def __init__(self, *args, **kwargs):
        super(BackupScreen, self).__init__(*args, **kwargs)
        self.app = MDApp.get_running_app()
        self.app.open_backup = self.switch_screen
        self.config = self.app.config
        self.set_config()
        self.set_current_settings()
        self.create_dialog = None
        self.clean_dialog = None
        self.ensure_backup_dir()
        self.backup_exists = os.path.exists("{}/backup.zip".format(self.backup_destination_path)) if True else False

    def report_error(self, exc, dt):
        Snackbar(
            text="[color=#f2776d]ERROR: {}[/color]".format(exc),
            size_hint_x=0.7,
            snackbar_y="30dp",
            snackbar_x="30dp",
            bg_color=get_color_from_hex("#544746")
        ).open()

    def report_info(self, message, dt):
        Snackbar(
            text="[color=#333333]INFO: {}[/color]".format(message),
            size_hint_x=0.7,
            snackbar_y="30dp",
            snackbar_x="30dp",
            bg_color=get_color_from_hex("#e3dede")
        ).open()

    def _refresh_config(func):
        def wrapper(self, *args, **kwargs):
            self.set_config()
            return func(self, *args, **kwargs)
        return wrapper

    def switch_screen(self, *args):
        if self.manager.current != self.name:
            self.manager.current = self.name

    def set_config(self):
        self.backup_destination_path = self.config.get("backup", "destination_path")
        self.game_dir = self.config.get("acc", "skins_dir")
        self.customs_path = "{}\\Customs".format(self.game_dir)
        self.liveries_path = "{}\\Liveries".format(self.customs_path)
        self.cars_path = "{}\\Cars".format(self.customs_path)

    def set_current_settings(self):
        self.ids.backup_label.text = "{}\n{}".format(self.ids.backup_label.text, self.config.get('backup', 'destination_path'))

    def ensure_backup_dir(self):
        if self.backup_destination_path != "":
            os.makedirs(self.backup_destination_path, exist_ok=True)
        else:
            raise Exception("Backup destination path is empty!")

    @_refresh_config
    def create_backup(self, skip_dialog=False):

        def action_cancel(*args):
            self.create_dialog.dismiss()

        def action_confirm(*args):
            try:
                with ZipFile('{}\\backup.zip'.format(self.backup_destination_path), 'w') as f:
                    for root, _, files in os.walk(self.cars_path):
                        for file in files:
                            f.write(os.path.join(root, file), 'Customs/Cars/{}'.format(file))

                    for root, _, files in os.walk(self.liveries_path):
                        for file in files:
                            f.write(os.path.join(root, file), "Customs/Liveries/{}/{}".format(os.path.basename(root), file))
                    self.backup_exists = True
                    self.create_dialog.dismiss()
                    Clock.schedule_once(partial(self.report_info, "Backup created!"))
            except Exception as exc:
                Clock.schedule_once(partial(self.report_error, exc))

        if not self.create_dialog:
            self.create_dialog = MDDialog(
                title="Overwrite backup",
                text="Backup already exist, do you want to overwrite?",
                buttons=[
                    MDFlatButton(
                        text="Cancel", on_release=action_cancel
                    ),
                    MDFlatButton(
                        text="Confirm", on_release=action_confirm
                    ),
                ],
            )

        if not self.backup_exists:
            action_confirm()
        elif not skip_dialog and self.backup_exists:
            self.create_dialog.open()

    @_refresh_config
    def restore_backup(self):
        try:
            if not self.backup_exists:
                raise Exception("Backup does not exist!")
            self.clean_customs(skip_dialog=True)
            with ZipFile("{}/backup.zip".format(self.backup_destination_path), 'r') as zip_ref:
                    zip_ref.extractall(self.game_dir)
            self.app.custom_dispatcher.do_refresh()
            Clock.schedule_once(partial(self.report_info, "Backup restored!"))
        except Exception as exc:
                Clock.schedule_once(partial(self.report_error, exc))

    @_refresh_config
    def clean_customs(self, skip_dialog=False):

        def action_cancel(*args):
            self.clean_dialog.dismiss()

        def action_confirm(*args):
            try:
                shutil.rmtree(self.liveries_path)
                shutil.rmtree(self.cars_path)

                os.makedirs(self.liveries_path, exist_ok=True)
                os.makedirs(self.cars_path, exist_ok=True)

                self.clean_dialog.dismiss()
                if not skip_dialog:
                    self.app.custom_dispatcher.do_refresh()
                    Clock.schedule_once(partial(self.report_info, "Customs/Cars and Customs/Liveries are clean now!"))
            except Exception as exc:
                Clock.schedule_once(partial(self.report_error, exc))

        if not self.clean_dialog:
            self.clean_dialog = MDDialog(
                title="Clean Customs",
                text="This action will remove all files under Customs/Cars and Customs/Liveries.\n\nMake sure you have backup of your data.\n\nDo you want to continue?",
                buttons=[
                    MDFlatButton(
                        text="Cancel", on_release=action_cancel
                    ),
                    MDFlatButton(
                        text="Confirm", on_release=action_confirm
                    ),
                ],
            )
        if not skip_dialog:
            self.clean_dialog.open()
        else:
            action_confirm()


class SkinScreen(MDScreen):

    def __init__(self, id_, *args, **kwargs):
        self.id = str(id_)
        self.name = str(id_)
        super(SkinScreen, self).__init__(*args, **kwargs)
