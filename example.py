import hate
""" hate is about websites for robots 

    at the client end:
        you open a page that represents an object
        following a link and filling a form is calling a method on the page
        the same library is used for every service

    at the server end:
        you map some objects to some urls
        when you get an object, you get a page back with data, links and forms
        generated from the methods and state of the object.

    the machine readable page
        language neutral, json-like objects, based on bencode 


    by using links and forms, the actual api can be loosely coupled
    you can redirect to other objects/services and grow the api without having to
    upgrade the client libraries.

    this example uses 'transient objects' 
        these objects can be serialized into urls, and passed around in links
        and forms. the object lives as long as the request.

        an example is url /message?id=blah
        we do not need to keep an object around for every message,
        but we can construct one on the request that knows how to retrieve the contents

        this is a short step towards stateless gateway services-
            e.g a stateless wrapper around a direct database connection

        I haven't done this in this example. I am bad.
    
        

"""

def client(endpoint):
    broker = hate.get(endpoint)
    # broker is a page, with a single element, 'queue' which is a form
    queue = broker.queue(name='help')
    # submitting this form takes us to the page for the queue
    print queue.push
    queue.push('help')
    # queue has two forms, 'push', 'pop'
    print queue.pop()


def server():
    import collections

    queues = {}

    m = hate.map()

    # these are created on each request
    @m.default()
    class Broker(hate.r):
        def queue(self, name):
            raise hate.Redirect(Queue(name))

    # the url parameters are used to construct them
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

