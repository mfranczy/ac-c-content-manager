from functools import partial

from kivy.clock import mainthread, Clock
from kivymd.app import MDApp
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.button import MDRectangleFlatButton, MDRectangleFlatIconButton
from kivymd.uix.progressbar import MDProgressBar
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.label import MDLabel
from kivy.utils import get_color_from_hex
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.behaviors import HoverBehavior
from kivymd.theming import ThemableBehavior
from kivymd.uix.behaviors import TouchBehavior
from kivy.properties import ObjectProperty, BooleanProperty, NumericProperty
from kivy.metrics import dp

from app.clients import LocalFileClient, HTTPClient
from app.threads import ThreadPool


class ToolbarItemWidget(MDBoxLayout, ThemableBehavior, HoverBehavior, TouchBehavior):

    def __init__(self, *args, **kwargs):
        self.action = ObjectProperty(None)
        self.hover = BooleanProperty(defaultvalue=True)
        super(ToolbarItemWidget, self).__init__(*args, **kwargs)

    def on_enter(self, *args):
        if not self.hover:
            return

        self.md_bg_color = get_color_from_hex("#ff5656")
        for obj in self.children:
            obj.text_color = get_color_from_hex("#ffffff")

    def on_leave(self, *args):
        if not self.hover:
            return

        self.md_bg_color = get_color_from_hex("#333333")
        for obj in self.children:
            obj.text_color = get_color_from_hex("#ff5656")

    def on_touch_down(self, mouse_event):
        if self.collide_point(mouse_event.pos[0], mouse_event.pos[1]):
            self.action()


class LeagueButtonWidget(MDRectangleFlatButton):
    # MDToggleButton does not work well with customization thus I do it this way 

    def __init__(self, id_, text, active, color, *args, **kwargs):
        self.app = MDApp.get_running_app()

        self.text = "[b]{}[/b]".format(text.upper())
        self.base_color = get_color_from_hex(color)
        self.secondary_color = get_color_from_hex("#222222")
        self.text_color = self.base_color
        self.line_color = self.base_color
        self.md_bg_color = self.secondary_color

        self.id = id_
        self.active = active

        if self.active:
            self.set_active()
        else:
            self.set_deactive()

        super(LeagueButtonWidget, self).__init__(*args, **kwargs)

    def on_md_bg_color(self, instance, value):
        self.md_bg_color = value

    def set_active(self, *args):
        self.text_color = get_color_from_hex("#222222")
        self.md_bg_color = self.base_color

    def set_deactive(self):
        self.md_bg_color = self.secondary_color
        self.text_color = self.base_color

    def on_release(self):
        for button in self.app.root.content.ids.leagues_buttons.children:
            button.set_deactive()

        self.set_active()
        self.app.root.content.ids.content_manager.current = self.id


class SkinWidget(MDGridLayout):

    _STATE_MISSING = "missing"
    _STATE_RECREATE = "recreate"
    _STATE_DOWNLOAD = "download"
    _STATE_UPDATE = "update"

    __slots__ = ('id', 'desc_label', 'percentage_label', 'progressbar', 'download_button', 'temp_size')

    def __init__(self, league_id, skin, skin_type):
        self.app = MDApp.get_running_app()

        # TODO: do refactoring of fields, it's a mess now
        self.sum_control = skin.get('sum')
        self.skin_name, self.skin_ext = skin.get('skin_name').split('.')
        
        # HACKY - FIX ME, the field should not be called car_name
        s = self.skin_name.split("-") 
        self.car_name = s[1]
        # END OF FIX ME

        self.league_id = league_id
        self.skin_type = skin_type
        self.league_color = skin.get('league_color_rgb')

        # new fields
        self.driver_name = skin.get('driver_name', '')
        self.team_name = skin.get('team_name', '')
        self.league_name = skin.get('league_name', '')
        self.league_type = skin.get('league_type', 'single')
        self.car_name_ext = skin.get('car_name', '')
        self.car_class = skin.get('car_class', '')
        self.car_year = str(skin.get('car_year', ''))
        self.car_number = str(skin.get('number', ''))

        self.remote_skin_path = '/api/skins/{}/{}/{}/download'.format(self.league_id, self.car_name, self.skin_name)
        self.remote_timestamp = skin.get('timestamp')
        super(SkinWidget, self).__init__()

        self.pool = ThreadPool()
        self.config = self.app.config
        self.dispatcher = self.app.custom_dispatcher

        self.http_client = HTTPClient()
        self.local_file = LocalFileClient(self.skin_type, self.car_name, self.skin_name, self.skin_ext)

        self.set_attr()
        self.register_events()
        Clock.schedule_once(self.initialize_data)
        Clock.schedule_once(self.refresh_state)
        self.download_in_progress = False

    def initialize_data(self, dt):
        self.league_color_bar.md_bg_color = get_color_from_hex(self.league_color)
        self.desc_label.car_number.text = "[b]{}[/b]".format(self.car_number)
        self.desc_label.car_model.text = self.car_name_ext
        if self.league_type == 'swap':
            self.desc_label.driver_name.text = "[b]{}[/b]".format(self.team_name)
            self.desc_label.team_name.text = ""
        else:
            self.desc_label.driver_name.text = "[b]{}[/b]".format(self.driver_name)
            self.desc_label.team_name.text = self.team_name

    def on_refresh(self, *args):
        Clock.schedule_once(self.refresh_state)

    @mainthread
    def refresh_state(self, dt):
        recreate_color = get_color_from_hex("#00cc00")
        download_color = get_color_from_hex("#00cc00")
        update_color = get_color_from_hex("#00cc00")
        if not self.local_file.car_exists and self.skin_type == 'ac':
            # Car files missing - cannot install skins
            self.state = self._STATE_MISSING

            self.download_button.disabled = True
            self.download_button.text = "MISSING CAR"
            self.download_button.icon = "sync-off"
            self.percentage_label.text = "[b]0%[/b]"
            self.percentage_label.text_color = get_color_from_hex("#ffffff")
            self.progressbar.width = 150
        elif self.local_file.car_exists and self.local_file.skin_exists:
            if self.remote_timestamp > self.local_file.timestamp:
                # Files downloaded but new version discovered on the server - update phase
                self.state = self._STATE_UPDATE

                self.progressbar.color = update_color
                self.download_button.disabled = False
                self.progressbar.color = update_color
                self.download_button.text = "[b]UPDATE[/b]"
                self.download_button.icon = "autorenew"
                self.progressbar.value = 0
                self.progressbar.width = 150
                self.percentage_label.text = "[b]0%[/b]"
                self.percentage_label.text_color = get_color_from_hex("#ffffff")
            else:
                # Files downloaded, everything up to date - recreate phase
                self.state = self._STATE_RECREATE
                self.download_button.disabled = False
                self.download_button.text = "[b]RECREATE[/b]"
                self.percentage_label.text = "[b]READY[/b]"
                self.progressbar.width = 0
                self.progressbar.value = 0
                self.download_button.icon = "autorenew"
                self.percentage_label.text_color = recreate_color
        else:
            # Skin files missing - download phase
            self.state = self._STATE_DOWNLOAD

            self.download_button.disabled = False
            self.progressbar.color = download_color
            self.download_button.text = "[b]DOWNLOAD[/b]"
            self.download_button.icon = "arrow-down-bold"
            self.progressbar.value = 0
            self.progressbar.width = 150
            self.percentage_label.text = "[b]0%[/b]"
            self.percentage_label.text_color = get_color_from_hex("#ffffff")

    def set_attr(self):
        # TODO: dirty hack - fix me
        for obj in self.children[0].children:
            setattr(self, obj.name, obj)
        self.temp_size = 0

        if hasattr(self, "progress_bar_box"):
            for obj in self.progress_bar_box.children:
                setattr(self, obj.name, obj)
        
        if hasattr(self, "download_box"):
            for obj in self.download_box.children:
                setattr(self, obj.name, obj)

    def register_events(self):
        self.download_button.bind(on_release=self.download_start)
        self.dispatcher.bind(on_refresh=self.on_refresh)
        self.dispatcher.bind(on_recreate_all=self.download_start)
        self.dispatcher.bind(on_download_all=self.on_download_all)

    def unregister_events(self):
        self.download_button.unbind(on_release=self.download_start)
        self.dispatcher.unbind(on_refresh=self.on_refresh)
        self.dispatcher.unbind(on_recreate_all=self.download_start)
        self.dispatcher.unbind(on_download_all=self.on_download_all)

    def on_download_all(self, *args):
        current_league_id = self.app.root.content.ids.content_manager.current
        if self.league_id == current_league_id and self.state in (self._STATE_DOWNLOAD, self._STATE_UPDATE):
            self.download_start()

    def download_start(self, *args):
        self.progressbar.width = 150
        self.percentage_label.text = "[b]0%[/b]"
        self.percentage_label.text_color = get_color_from_hex("#ffffff")
        if self.download_in_progress:
            return
        self.download_in_progress = True
        self.temp_size = 0
        Clock.schedule_once(self.set_pre_download_btn_ui)

        def _download():            
            try:
                temp_file = self.local_file.create_temp()
                self.http_client.download_file(self.remote_skin_path, temp_file, self.download_progress)
                self.local_file.extract_temp()
            except Exception as exc:
                Clock.schedule_once(partial(self.report_error, exc))
            finally:
                Clock.schedule_once(self.refresh_state)
                self.download_in_progress = False

        self.pool.submit(_download)

    def report_error(self, exc, dt):
        Snackbar(
            text="[color=#f2776d]ERROR: {}[/color]".format(exc),
            size_hint_x=1,
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
        self.percentage_label.text = "[b]0%[/b]"
        self.download_button.disabled = True

    @mainthread
    def update_progress_bar(self, percent, dt):
        self.progressbar.value = percent
        self.percentage_label.text = "[b]{}%[/b]".format(percent)


class DescriptionLabelWidget(MDBoxLayout):

    def __init__(self, *args, **kwargs):
        self.name = "desc_label"
        super(DescriptionLabelWidget, self).__init__(*args, **kwargs)
        self.add_widget(TextLabelWidget('car_number', 50, None, "#FFFFFF", (10, 10), "center"))
        self.add_widget(TextLabelWidget('driver_name', 0, 0.1, "#FFFFFF", (0, 0), "left"))
        self.add_widget(TextLabelWidget('car_model', 0, 0.1, "#B3B6B8", (0, 0), "left"))
        self.add_widget(TextLabelWidget('team_name', 0, 0.1, "#B3B6B8", (0, 0), "left"))
        self.set_attr()

    def set_attr(self):
        for obj in self.children:
            setattr(self, obj.name, obj)
        self.temp_size = 0


class TextLabelWidget(MDLabel):
    
    def __init__(self, name, width, size_hint_x, text_color, padding, halign, *args, **kwargs):
        self.name = name
        self.theme_text_color = 'Custom'
        self.padding_x = padding
        self.text_color = get_color_from_hex(text_color)
        self.size_hint_x = size_hint_x
        self.halign = halign
        self.width = width
        self.font_style = 'Body2'
        self.markup = True
        super(TextLabelWidget, self).__init__(*args, **kwargs)


class PercentageLabelWidget(MDLabel):
    
    def __init__(self, *args, **kwargs):
        self.name = "percentage_label"
        super(PercentageLabelWidget, self).__init__(*args, **kwargs)


class ProgressBarWidget(MDProgressBar):
    
    def __init__(self, *args, **kwargs):
        self.name = "progressbar"
        super(ProgressBarWidget, self).__init__(*args, **kwargs)


class DownloadWidget(MDRectangleFlatIconButton):
    
    def __init__(self, *args, **kwargs):
        self.name = "download_button"
        super(DownloadWidget, self).__init__(*args, **kwargs)
