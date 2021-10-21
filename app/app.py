import winreg
import os

from kivymd.effects.stiffscroll import StiffScrollEffect # hack for pyinstaller
from pathlib import Path

os.environ['KIVY_HOME'] = r'{}\Documents\Simrace Content Manager'.format(Path.home())

from kivy.config import Config
Config.set('graphics', 'width', '1024')
Config.set('graphics', 'height', '768')

from kivymd.app import MDApp
from .screens import MainScreen, SettingsScreen
from .dispatcher import CustomDispatcher


class App(MDApp):
    
    def __init__(self, *args, **kwargs):
        self.custom_dispatcher = CustomDispatcher()
        super(App, self).__init__(*args, **kwargs)

    def build_config(self, config):
        def _get_ac_dir():
            try:
                hkey = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\WOW6432Node\Valve\Steam")
                steam_path = winreg.QueryValueEx(hkey, "InstallPath")[0]
                winreg.CloseKey(hkey)
            except Exception as exc:
                print(exc)
                return ""
            else:
                if steam_path == "":
                    return ""
                return r'{}\steamapps\common\assettocorsa\content\cars'.format(steam_path)

        def _get_acc_dir():
            d = Path(r'{}\Documents\Assetto Corsa Competizione'.format(Path.home()))
            if d.exists():
                return str(d.absolute())
            return ""
        
        config.setdefaults('generic', {
                'user': '',
                'password': '',
                'server': 'https://esport.simrace.pl'
            }
        )

        config.setdefaults('ac', {
                'skins_dir': _get_ac_dir() 
            },
        )

        config.setdefaults('acc', {
                'skins_dir': _get_acc_dir() 
            },
        )

        config.setdefaults('backup', {
                "destination_path": "{}\\backup".format(os.environ['KIVY_HOME'])
            },
        )

    def create_settings(self):
        return SettingsScreen()

    def build(self):
        self.title = "simrace.pl - build v0.1.0-alpha-5"
        self.icon = "icon.ico"
        return MainScreen()
