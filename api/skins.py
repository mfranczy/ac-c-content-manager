from client import Client
from functools import partial


class Skin:

    def __init__(self, client, file, skins_destination):
        self.__client = client
        self.file = file
        self.skins_destination = skins_destination
        self.progress_bar_clbk = None
        self.size = 0
        self.max_size = 0

    def set_progress_bar_clbk(self, clbk):
        self.progress_bar_clbk = clbk

    @property
    def is_up_to_date(self):
        pass

    @property
    def exists(self):
        pass

    def set_size(self, size):
        self.size = size

    def remove(self):
        pass

    def download(self):
        if self.size > 0:
            self.size = 0
        self.__client.download_file(self.file, self.skins_destination, partial(self.write_callback))

    def write_callback(self, max_size, fd, data):    
        fd.write(data)
        self.size += len(data)
        self.max_size = max_size
        self.progress_bar_clbk(self.size, max_size)
        # TODO: extract 7z files


class Skins:
    skins = {}

    def __init__(self, endpoint, skins_destination):
        self.skins_destination = skins_destination
        self.__client = Client(endpoint)

    def list(self):
        for file in self.__client.list_external_files():
            self.skins[file] = Skin(self.__client, file, self.skins_destination)
        return self.skins

    def remove(self):
        pass
