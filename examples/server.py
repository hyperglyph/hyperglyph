import hyperglyph
import collections

queues = {}

m = hyperglyph.Router()

@m.add()
class Queue(hyperglyph.r):
    def __init__(self, name):
        self.name = name
    def push(self, msg):
        if self.name not in queues:
            queues[self.name]=collections.deque()
        queues[self.name].appendleft(msg)

    def pop(self):
        if self.name in queues:
            return queues[self.name].popleft()

s = hyperglyph.Server(m, port=12344)

s.start()

print s.url
try:
    while s.is_alive():
        s.join(2)
finally:
    s.stop()


