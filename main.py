import os, sys
from kivy.resources import resource_add_path, resource_find

from app import App

if __name__ == '__main__':
    if hasattr(sys, '_MEIPASS'):
        resource_add_path(os.path.join(sys._MEIPASS))
    App().run()
