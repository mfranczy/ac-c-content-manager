from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
from abc import ABC, abstractmethod

from client.pool import ThreadPool


class NetworkClient(ABC):

    def __init__(self, **kwargs):
        super(NetworkClient, self).__init__(**kwargs)
        self.pool = ThreadPool()

    @abstractmethod
    async def list_files(self):
        pass

    @abstractmethod
    async def download_file(self, file, dest, callback):
        pass
