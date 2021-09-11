from kivymd.app import MDApp
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.button import MDRectangleFlatButton
from kivymd.uix.progressbar import MDProgressBar
from kivymd.uix.label import MDLabel
from kivy.utils import get_color_from_hex

from .clients import FTPClient, LocalFileClient


class SkinWidget(MDGridLayout):

    __slots__ = ('id', 'desc_label', 'percentage_label', 'progressbar', 'download_button', 'temp_size')

    def __init__(self, remote_skin_path, remote_timestamp, skin_type):
        self.config = MDApp.get_running_app().config
        self.remote_timestamp = remote_timestamp
        self.remote_skin_path = remote_skin_path
        super(SkinWidget, self).__init__()

        self.ftp = FTPClient()
        self.local_file = LocalFileClient(remote_skin_path, self.config.get(skin_type, "cars_dir"))

        self.set_attr()
        self.register_events()
        self.set_description()
        self.refresh_state()

    @property
    def name(self):
        s = self.remote_skin_path.split("/")
        return "{}/{}".format(s[2], s[3])

    def set_description(self):
        self.desc_label.text = self.name

    def refresh_state(self):
        recreate_color = get_color_from_hex("#00cc00")
        download_color = get_color_from_hex("#ff8000")
        update_color = get_color_from_hex("#03fcf8")
        lock_color = get_color_from_hex("#ff0000")

        if not self.local_file.car_exists:
            # Car files missing - cannot install skins
            self.download_button.disabled = True
            self.download_button.lock_color = lock_color
            self.download_button.md_bg_color_disabled = get_color_from_hex("#eb4034")
            self.download_button.text = "Missing car"
        elif self.local_file.skin_exists:
            if self.remote_timestamp > self.local_file.timestamp:
                # Files downloaded but new version discovered on the server - update phase
                self.progressbar.color = update_color
                self.download_button.disabled = False
                self.download_button.line_color = update_color
                self.download_button.text = "Update"
                self.progressbar.value = 0
                self.percentage_label.text = "0%"
            else:
                # Files downloaded, everything up to date - refresh phase
                self.download_button.disabled = False
                self.progressbar.color = recreate_color
                self.download_button.line_color = recreate_color
                self.download_button.text = "Recreate"
                self.progressbar.value = 100
                self.percentage_label.text = "100%"
        else:
            # Skin files missing - download phase
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

    def download_start(self, obj):
        self.temp_size = 0
        self.progressbar.value = 0
        self.percentage_label.text = "0%"
        self.download_button.disabled = True
        self.download_button.md_bg_color_disabled = get_color_from_hex("#ffd970")
        self.download_button.text = "Downloading"
        temp_file = self.local_file.create_temp()
        self.ftp.download_file(self.remote_skin_path, temp_file, self.download_progress)

    def download_progress(self, max_size, fd, data):
        try:
            fd.write(data)
            self.temp_size += len(data)
            percent = int(self.temp_size * 100 / max_size)
            self.progressbar.value = percent
            self.percentage_label.text = "{}%".format(percent)
            if percent >= 100:
                self.local_file.extract_temp()
                self.refresh_state()
        except Exception as exc:
            print(exc)
            self.refresh_state()


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

    