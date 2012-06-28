import glyph

def server():
    import collections

    queues = {}

    m = glyph.Router()

    # these are created on each request

    # the url parameters are used to construct them
    @m.add()
    class Queue(glyph.r):
        def __init__(self, name):
            self.name = name
        def push(self, msg):
            if self.name not in queues:
                queues[self.name]=collections.deque()
            queues[self.name].appendleft(msg)

        def pop(self):
            if self.name in queues:
                return queues[self.name].popleft()

    s = glyph.Server(m, port=12344)
    s.start()
    print s.url
    try:
        while s.is_alive():
            s.join(2)
    finally:
        s.stop()

if __name__ == '__main__':
        server()

