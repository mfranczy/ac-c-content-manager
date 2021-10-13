from functools import partial

from kivy.clock import mainthread, Clock
from kivymd.app import MDApp
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.button import MDRectangleFlatButton
from kivymd.uix.progressbar import MDProgressBar
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.label import MDLabel
from kivy.utils import get_color_from_hex
from kivy.metrics import dp
from kivymd.uix.menu import MDDropdownMenu

from app.clients import LocalFileClient, HTTPClient
from app.threads import ThreadPool


class MenuWidget(MDDropdownMenu):

    def __init__(self, disabled_items=[], *args, **kwargs):
        self.app = MDApp.get_running_app()
        self.dispatcher = self.app.custom_dispatcher
        self.width_mult = 4
        self.items = self.menu_items(disabled_items)
        super(MenuWidget, self).__init__(*args, **kwargs)
        

    def open_callback(self, button):
        self.caller = button
        self.open()

    def menu_items(self, disabled_items):
        items = [
            {
                "name": "refresh",
                "viewclass": "OneLineListItem",
                "text": "Refresh",
                "height": dp(56),
                "on_release": self.refresh,
            },
            {
                "name": "recreate_all",
                "viewclass": "OneLineListItem",
                "text": "Recreate all",
                "height": dp(56),
                "on_release": self.recreate_all,
            },
            {
                "name": "download_all",
                "viewclass": "OneLineListItem",
                "text": "Download all",
                "height": dp(56),
                "on_release": self.download_all,
            },
            {
                "name": "settings",
                "viewclass": "OneLineListItem",
                "text": "Settings",
                "height": dp(56),
                "on_release": self.app.open_settings,
            }
        ]
        
        result = []
        for item in items:
            if item["name"] in disabled_items:
                continue
            result.append(item)
        return result

    def _menu_item(func):
        def wrapper(self):
            func(self)
            self.dismiss()
        return wrapper

    def menu_callback(self, text_item):
        self.dismiss()
        Snackbar(text=text_item).open()

    @_menu_item
    def refresh(self):
        self.dispatcher.do_refresh()

    @_menu_item
    def recreate_all(self):
        self.dispatcher.do_recreate_all()

    @_menu_item
    def download_all(self):
        self.dispatcher.do_download_all()


class SkinWidget(MDGridLayout):

    _STATE_MISSING = "missing"
    _STATE_RECREATE = "recreate"
    _STATE_DOWNLOAD = "download"
    _STATE_UPDATE = "update"

    __slots__ = ('id', 'desc_label', 'percentage_label', 'progressbar', 'download_button', 'temp_size')

    def __init__(self, skin, skin_type):
        self.sum_control = skin.get('sum')
        self.car_name = skin.get('car_name')
        self.skin_name, self.skin_ext = skin.get('skin_name').split('.')
        self.league_id = skin.get('league_id')
        self.skin_type = skin_type
        self.remote_skin_path = '/api/skins/{}/{}/{}/download'.format(self.league_id, self.car_name, self.skin_name)
        super(SkinWidget, self).__init__()

        self.pool = ThreadPool()
        app = MDApp.get_running_app()
        self.config = app.config
        self.dispatcher = app.custom_dispatcher
        self.dispatcher.bind(on_refresh=self.on_refresh)

        self.http_client = HTTPClient()
        self.local_file = LocalFileClient(self.skin_type, self.config.get(self.skin_type, "skins_dir"), self.car_name, self.skin_name, self.skin_ext)

        self.set_attr()
        self.register_events()
        Clock.schedule_once(self.set_description)
        Clock.schedule_once(self.refresh_state)
        self.download_in_progress = False
        self.refresh_required = False

    @property
    def name(self):
        return "{}/{}".format(self.car_name, self.skin_name)

    def set_description(self, dt):
        self.desc_label.text = self.name

    def on_refresh(self, *args):
        Clock.schedule_once(self.refresh_state)

    @mainthread
    def refresh_state(self, dt):
        recreate_color = get_color_from_hex("#00cc00")
        download_color = get_color_from_hex("#ff8000")
        update_color = get_color_from_hex("#03fcf8")
        lock_color = get_color_from_hex("#ff0000")

        if not self.local_file.car_exists and self.skin_type == 'ac':
            # Car files missing - cannot install skins
            self.state = self._STATE_MISSING

            self.download_button.disabled = True
            self.download_button.lock_color = lock_color
            self.download_button.md_bg_color_disabled = get_color_from_hex("#e85d1c")
            self.download_button.text = "Missing car"
        elif self.local_file.car_exists and self.local_file.skin_exists:
            if self.refresh_required:
                # Files downloaded but new version discovered on the server - update phase
                self.state = self._STATE_UPDATE

                self.progressbar.color = update_color
                self.download_button.disabled = False
                self.progressbar.color = update_color
                self.download_button.line_color = update_color
                self.download_button.text = "Update"
                self.progressbar.value = 0
                self.percentage_label.text = "0%"
            else:
                # Files downloaded, everything up to date - recreate phase
                self.state = self._STATE_RECREATE

                self.download_button.disabled = False
                self.progressbar.color = recreate_color
                self.download_button.line_color = recreate_color
                self.download_button.text = "Recreate"
                self.progressbar.value = 100
                self.percentage_label.text = "100%"
        else:
            # Skin files missing - download phase
            self.state = self._STATE_DOWNLOAD

            self.download_button.disabled = False
            self.progressbar.color = download_color
            self.download_button.line_color = download_color
            self.download_button.text = "Download"
            self.progressbar.value = 0
            self.percentage_label.text = "0%"

    def set_attr(self):
        for obj in self.children:
            setattr(self, obj.name, obj)
        self.temp_size = 0

    def register_events(self):
        self.download_button.bind(on_release=self.download_start)
        self.dispatcher.bind(on_recreate_all=self.download_start)
        self.dispatcher.bind(on_download_all=self.on_download_all)

    def on_download_all(self, *args):
        if self.state in (self._STATE_DOWNLOAD, self._STATE_UPDATE):
            self.download_start()

    def download_start(self, *args):
        if self.download_in_progress:
            return
        self.download_in_progress = True

        self.temp_size = 0
        Clock.schedule_once(self.set_pre_download_btn_ui)

        def _download():            
            try:
                Clock.schedule_once(self.set_download_btn_ui)
                temp_file = self.local_file.create_temp()
                self.http_client.download_file(self.remote_skin_path, temp_file, self.download_progress)
                Clock.schedule_once(self.set_extract_btn_ui)
                self.local_file.extract_temp()
            except Exception as exc:
                Clock.schedule_once(partial(self.report_error, exc))
            finally:
                Clock.schedule_once(self.refresh_state)
                self.download_in_progress = False
                self.refresh_required = False

        self.pool.submit(_download)

    def report_error(self, exc, dt):
        Snackbar(
            text="[color=#f2776d]ERROR: {}[/color]".format(exc),
            size_hint_x=.7,
            snackbar_y="30dp",
            snackbar_x="30dp",
            bg_color=get_color_from_hex("#544746")
        ).open()

    def download_progress(self, max_size, chunk_size):
        self.temp_size += chunk_size
        percent = int(self.temp_size * 100 / max_size)
        Clock.schedule_once(partial(self.update_progress_bar, percent))

    @mainthread
    def set_pre_download_btn_ui(self, dt):
        self.progressbar.value = 0
        self.percentage_label.text = "0%"
        self.download_button.disabled = True
        self.download_button.md_bg_color_disabled = get_color_from_hex("#cd8dd8")
        self.download_button.text = "Waiting"

    @mainthread
    def set_download_btn_ui(self, dt):
        self.download_button.text = "Downloading"
        self.download_button.md_bg_color_disabled = get_color_from_hex("#dad239")

    @mainthread    
    def set_extract_btn_ui(self, dt):
        self.download_button.text = "Extracting"
        self.download_button.md_bg_color_disabled = get_color_from_hex("#54f0af")

    @mainthread
    def update_progress_bar(self, percent, dt):
        self.progressbar.value = percent
        self.percentage_label.text = "{}%".format(percent)


class DescriptionLabelWidget(MDLabel):

    def __init__(self, *args, **kwargs):
        self.name = "desc_label"
        super(DescriptionLabelWidget, self).__init__(*args, **kwargs)


class PercentageLabelWidget(MDLabel):
    
    def __init__(self, *args, **kwargs):
        self.name = "percentage_label"
        super(PercentageLabelWidget, self).__init__(*args, **kwargs)


class ProgressBarWidget(MDProgressBar):
    
    def __init__(self, *args, **kwargs):
        self.name = "progressbar"
        super(ProgressBarWidget, self).__init__(*args, **kwargs)


class DownloadWidget(MDRectangleFlatButton):
    
    def __init__(self, *args, **kwargs):
        self.name = "download_button"
        super(DownloadWidget, self).__init__(*args, **kwargs)

    