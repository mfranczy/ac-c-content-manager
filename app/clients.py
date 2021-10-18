import os
import shutil
import tempfile
import zipfile
import requests

from datetime import datetime
from pytz import timezone
from requests.auth import HTTPBasicAuth
from pathlib import Path
from urllib.parse import urlparse

from kivymd.app import MDApp


def cet_timestamp(ts):
    dt = datetime.fromtimestamp(ts)
    dt = dt.astimezone(timezone('Europe/Warsaw'))
    return dt.timestamp()


class HTTPClient:

    def __init__(self):
        self.config = MDApp.get_running_app().config
        self.set_config()

    def set_config(self):
        self.user = self.config.get('generic', 'user')
        self.password = self.config.get('generic', 'password')
        self.server = self.config.get('generic', 'server')
        self.scheme = urlparse(self.server)
    
    def _refresh_config(func):
        def wrapper(self, *args, **kwargs):
            self.set_config()
            return func(self, *args, **kwargs)
        return wrapper

    @_refresh_config
    def ping(self):
        resp = requests.get(self.server, auth=HTTPBasicAuth(self.user, self.password))
        if resp.status_code != 200:
            raise Exception("Response code {}".format(resp.status_code))

    @_refresh_config
    def list_skins(self):
        endpoint = self.server + "/api/skins/list"
        resp = requests.get(endpoint, auth=HTTPBasicAuth(self.user, self.password))
        return resp.json()

    @_refresh_config
    def download_file(self, endpoint, file, progress_callback):
        # TODO: validate this, it's very optimistic
        with file as fd:
            resp = requests.get(self.server + endpoint, auth=HTTPBasicAuth(self.user, self.password), stream=True)
            if resp.status_code != 200:
                raise Exception("Unable to download file, response code {}".format(resp.status_code))
            max_size = int(resp.headers.get('Content-Length', 0))
            for chunk in resp.iter_content(chunk_size=512):
                fd.write(chunk)
                progress_callback(max_size, len(chunk))


class LocalFileClient:

    def __init__(self, skin_type, car_name, skin_name, skin_ext):
        # TODO: validate this, it's very optimistic
        # TODO: refactor this to subclasses
        self.config = MDApp.get_running_app().config
        self.skin_type = skin_type
        self.car_name = car_name
        self.skin_name = skin_name
        self.skin_ext = skin_ext
        self.temp = None
        self.set_config()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.delete_temp()

    def set_config(self):
        cars_dir = self.config.get(self.skin_type, "skins_dir")
        if self.skin_type == 'ac':
            self.car_path = "{}/{}".format(cars_dir, self.car_name)
            self.extract_path = "{}/skins".format(self.car_path)
            self.skin_path = "{}/{}".format(self.extract_path, self.name)
        elif self.skin_type == 'acc':
            self.car_path = "{}/Customs/Cars/{}.json".format(cars_dir, self.skin_name)
            self.extract_path = cars_dir
            self.skin_path = "{}/Customs/Liveries/{}".format(self.extract_path, self.skin_name)
        else:
            raise Exception("Invalid skin type: {}".format(self.skin_type))

    def _refresh_config(func):
        def wrapper(self, *args, **kwargs):
            self.set_config()
            return func(self, *args, **kwargs)
        return wrapper

    @property
    @_refresh_config
    def car_exists(self):
        path = Path(self.car_path)
        if self.skin_type == 'ac':
            return path.is_dir()
        elif self.skin_type == 'acc':
            return path.is_file()

    @property
    @_refresh_config
    def skin_exists(self):
        path = Path(self.skin_path)
        return path.is_dir()

    @property
    @_refresh_config
    def timestamp(self):
        if not self.skin_exists:
            return None
        return cet_timestamp(os.path.getmtime(self.skin_path))

    def create_temp(self):
        self.temp = tempfile.NamedTemporaryFile(delete=False, suffix=".{}".format(self.skin_ext))
        return self.temp

    def delete_temp(self):
        return
        if self.temp is not None:
            shutil.rmtree(self.temp.name, ignore_errors=True)

    @_refresh_config
    def extract_temp(self):
        self.temp.close()
        try:
            with zipfile.ZipFile(self.temp.name, 'r') as zip_ref:
                zip_ref.extractall(self.extract_path)
        except Exception as exc:
            shutil.rmtree(self.skin_path)
            raise exc
        finally:
            self.delete_temp()
