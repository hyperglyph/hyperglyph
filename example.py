import hate

def client(endpoint):
    broker = hate.get(endpoint)
    queue = broker.queue(name='help')
    queue.push(msg='help')
    print queue.pop()


def server():
    import collections

    queues = {}

    m = hate.map()

    @m.default()
    class Broker(hate.r):
        def queue(self, name):
            raise hate.Redirect(Queue(name))

    @m.add()
    class Queue(hate.r):
        def __init__(self, name):
            self.name = name
        def push(self, msg):
            if self.name not in queues:
                queues[self.name]=collections.deque()
            queues[self.name].appendleft(msg)

        def pop(self):
            if self.name in queues:
                return queues[self.name].popleft()

    s = hate.Server(m)
    s.start()
    print s.url
    try:
        while s.is_alive():
            s.join(2)
    finally:
        s.stop()

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        client(sys.argv[1])
    else:
        server()

