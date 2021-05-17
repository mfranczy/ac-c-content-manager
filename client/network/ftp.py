from functools import partial
from ftplib import FTP, Error
from client.errors import ClientError

from . import NetworkClient


class FTPClient(NetworkClient):

    def __init__(self, endpoint):
        super(FTPClient, self).__init__()
        self.endpoint = endpoint

    def ping(self):
        with FTP(self.endpoint.hostname) as ftp:
            ftp.login()

    def list_files(self):
        try:
            with FTP(self.endpoint.hostname) as ftp:
                ftp.login()
                ftp.cwd(self.endpoint.path)
                return ftp.nlst()
        except Error as exc:
            raise ClientError(exc)

    # stale
    def abort_download(self):
        pass

    def download_file(self, file, dest, callback):

        def _download():
            with open(dest + file, "wb") as fd:
                with FTP(self.endpoint.hostname) as ftp:
                    try:
                        ftp.login()
                        ftp.cwd(self.endpoint.path)
                        size = ftp.size(file)
                        ftp.retrbinary("RETR " + file, partial(callback, size, fd))
                    except Exception as exc:
                        # TODO: change to thread exit
                        print(exc)

        self.pool.submit(_download)
