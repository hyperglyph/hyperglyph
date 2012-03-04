import glyph
from time import sleep

def worker(endpoint, name):
    s = glyph.get(endpoint)

    print name
    queue = s.task_queue(name)
    print queue


    t = queue.task()
    print t
    while t:
        print 'working on ', t.name
        for s in range(t.steps):
            t.progress(s)
            sleep(1)
        t.complete()
        t = queue.task()

def queue():
    import collections

    tasks = list("abcdefghijklmnopqrstuvwxyz")

    m = glyph.Router()

    @m.default()
    class Server(glyph.r):
        def task_queue(self, worker_name):
            print worker_name
            return Queue(worker_name)

    @m.add()
    class Queue(glyph.r):
        def __init__(self, worker_name):
            self.worker_name = worker_name

        def task(self):
            print self.worker_name
            return Task(self.worker_name, tasks.pop())

    @m.add()
    class Task(glyph.r):
        def __init__(self, _worker, name, steps=2):
            self._worker = _worker
            self.name = name
            self.steps = int(steps)

        def progress(self, msg):
            print self._worker, self.name, msg

        def complete(self):
            print self._worker, self.name, 'complete'

    s = glyph.Server(m)
    return s


if __name__ == '__main__':
    s = queue()
    s.start()

    worker(s.url, 'client')

    s.stop()

