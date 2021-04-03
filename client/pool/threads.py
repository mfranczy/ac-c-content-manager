import threading
import queue


class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


# this class is used to have better control over threads
# using ThreadPoolExecutor you don't have control over queue
# which will be required later in this project
class ThreadPool(metaclass=Singleton):

    def __init__(self, **kwargs):
        self.q = queue.Queue()
        self.workers_num = 5
        self.workers = []
        for i in range(self.workers_num):
            self.workers.append(
               threading.Thread(target=self.worker, kwargs={"q": self.q}, daemon=True).start()
            )

    def submit(self, item):
        self.q.put(item)


    def worker(self, q):
        while True:
            try:
                item = q.get()
                item()
                q.task_done()
            except Exception as exc:
                # TODO: change to better error handling
                print(exc)
