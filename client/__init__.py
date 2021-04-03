from urllib.parse import urlparse

from .errors import ClientError
from .network.ftp import FTPClient

__all__ = ["Client", "ClientError"]


class Client:

    def __init__(self, endpoint):
        self.endpoint = urlparse(endpoint)
        self.__local = None

    @property
    def __net(self):
        # if self.endpoint.scheme == "ftp":
        return FTPClient(self.endpoint)
        # raise NotImplementedError("endpoint does not have corresponding client")

    def download_file(self, file, dest, callback):
        self.__net.download_file(file, dest, callback)

    def list_external_files(self):
        return self.__net.list_files()

    def list_local_files(self):
        self.__local.list_files()
