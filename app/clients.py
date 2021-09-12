import os
import shutil
import time
import tempfile

from pyunpack import Archive
from pathlib import Path
from ftplib import FTP
from urllib.parse import urlparse
from functools import partial

from kivymd.app import MDApp


class FTPClient:

    def __init__(self):
        super(FTPClient, self).__init__()
        config = MDApp.get_running_app().config
        self.user = config.get('generic', 'user')
        self.server = config.get('generic', 'server')
        self.scheme = urlparse(self.server)

    def ping(self):
        with FTP(self.scheme.hostname) as ftp:
            ftp.login(user=self.user)

    def list_skins(self, base_path):
        result = []
        with FTP(self.scheme.hostname) as ftp:
            ftp.login(user=self.user)
            if base_path == "ac":
                # TODO: optimze loops, it's not needed to execute this bruteforce
                # TODO: better to verify if file should be refreshed over checksum than timestamp
                # although not every FTP server supports HASH command and there is no standard for hashing
                # result.append((skin, ftp.sendcmd("MDTM {}".format(skin))))
                ids = ftp.nlst(base_path)
                for id_ in ids:
                    cars = ftp.nlst(id_)
                    for car in cars:
                        skins = ftp.nlst(car)
                        for skin in skins:
                            for file in ftp.mlsd(skin):
                                if file[1]["type"] == "file":
                                    # TODO: set server timestamp, now there is assumption GMT+2
                                    timestamp = time.mktime(time.strptime(file[1]['modify'], "%Y%m%d%H%M%S"))
                                    result.append((skin,timestamp))
            elif base_path == "acc":
                pass
            else:
                raise Exception("Invalid base path")
            return result

    def download_file(self, file_path, file, progress_callback):
        with file as fd:
            with FTP(self.scheme.hostname) as ftp:
                ftp.login(user=self.user)
                size = ftp.size(file_path)
                ftp.retrbinary("RETR " + file_path, partial(progress_callback, size, fd))


class LocalFileClient:

    def __init__(self, remote_skin_path, cars_dir):
        # TODO: validate this, it's very optimistic
        res = remote_skin_path.split("/")
        self.name, self.ext = res[3].split(".")
        self.car_path = "{}/{}".format(cars_dir, res[2])
        self.skins_path = "{}/skins".format(self.car_path)
        self.skin_path = "{}/{}".format(self.skins_path, self.name)
        self.temp = None

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.temp is not None:
            shutil.rmtree(self.temp.name, ignore_errors=True)

    @property
    def car_exists(self):
        path = Path(self.car_path)
        return path.is_dir()

    @property
    def skin_exists(self):
        path = Path(self.skin_path)
        return path.is_dir()

    @property
    def timestamp(self):
        if not self.skin_exists:
            return None
        return os.path.getmtime(self.skin_path)

    def create_temp(self):
        self.temp = tempfile.NamedTemporaryFile(delete=False, suffix=".{}".format(self.ext))
        return self.temp

    def delete_temp(self):
        if self.temp is not None:
            shutil.rmtree(self.temp.name, ignore_errors=True)

    def extract_temp(self):
        self.temp.close()
        try:
            Archive(self.temp.name).extractall(self.skins_path, auto_create_dir=True)
            mod_time = time.time()
            # TODO: set server timestamp, now there is assumption GMT+2
            os.utime(self.skin_path, (mod_time, mod_time))
        except Exception as exc:
            shutil.rmtree(self.skin_path)
            raise exc
        finally:
            self.delete_temp()
