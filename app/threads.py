import threading
import queue


class Singleton(type):
    _instances = {}
    def __call__(self, *args, **kwargs):
        if self not in self._instances:
            self._instances[self] = super(Singleton, self).__call__(*args, **kwargs)
        return self._instances[self]


# this class is used to have better control over threads
# using ThreadPoolExecutor you don't have control over queue
# which will be required later in this project
class ThreadPool(metaclass=Singleton):

    def __init__(self, **kwargs):
        self.q = queue.Queue()
        self.workers_num = 5
        self.workers = []
        for _ in range(self.workers_num):
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
                # TODO: add better error handling
                print(exc)
