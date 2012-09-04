============================
 hyperglyph: duck typed ipc
============================

hyperglyph is ipc (inter process communication) for dynamic, duck typed languages. unlike
other ipc libraries, the server can return different objects
to the client, without the client breaking.

the protocol supports a reasonable selection of primitive datatypes, 
including integers, floating point, lists, sets, dictionaries, ordered
dictonaries, utf-8 strings, byte arrays, and datetimes/timedeltas.

hyperglyph works with existing http tools like caches and load balancers
to grow services, as well as supporting redirecting or linking 
to services on other hosts.

a talk at src-fringe 2012 was given and is online: http://vimeo.com/45474360
(before the project changed its name)

we're on irc.freenode.net #hyperglyph


license
-------

hyperglyph is released under the MIT license


status
------

hyperglyph is pre 1.0 software and so should be considered unstable
and experimental. however, earlier versions have been successfully
used in production for more than a year.

the underlying specification has been finalized, and the reference
implementations are catching up.

the ruby version trails behind the python version.

1.0 roadmap
-----------

- finalize spec (done)

- python implementation to spec (in progress)

  - client is complete
  - server does not make use of all the spec

- ruby implementation to spec (in progress, but slower)

  - client, server  is incomplete

- full coverage of specification by tests (in progress, but slower)

  - ruby, python individually tested
  - need cross implementation tests

- 1.0 release

  - documentation, tests, and two implementations complete


example
=======

To show, rather than tell, let's begin with some server code::

    import glyph

    r = glyph.Router() # a wsgi application

    @r.add()
    def hello():
        return "Hello World"

    # and a http server running in a thread
    s = glyph.Server(r) 
    s.start()

    print s.url
    s.join()

And some client code::

    import glyph 

    server = glyph.get('http://server/')

    print server.hello()

Adding a new function is simple::

    @r.add()
    def goodbye(name):
        return "Goodbye " + name

And you can change the functions a little::

    @r.add()
    def hello(name="World"):
        return "Hello "+name

Amazingly, The old client still works, without changes::

    print server.hello()

To call new methods, you just call them::

    print server.hello('dave')
    print server.goodbye('dave')

Functions can return lists, dicts, sets, byte strings, unicode,
dates, booleans, ints & floats::

    @r.add()
    def woo():
        return [1,True, None, False, "a",u"b"]

Functions can even return other functions that are mapped::

    @r.add()
    def greeting(lang="en"):
        if lang == "en":
            return hello
        elif lang == 'fr':
            return salut

The client doesn't care::

    greet = client.greeting()

    print greet()
    

Glyph can map objects too::

    @r.add()
    def find_user(name):
        user_id = database.find_user(name)
        return User(user_id)

    @r.add()
    class User(glyph.Resource):
        def __init__(self, id):
            self.id = id

        def message(self, subject, body):
            database.send_message(self.id, subject, body)

        def bio(self):
            return database.get_bio(self.id)

The client can get a User and find details::

    bob = server.find_user('bob')
    bob.messsage('lol', 'feels good man')

Like before, new methods can be added without breaking old clients.
unlike before, we can change object internals::

    @r.add()
    @glyph.redirect()
    def find_user(name):
        user_id, shard = database.find_user(name)
        return User(user_id, shard)

    @r.add()
    class User(glyph.Resource):
        def __init__(self, id, shard):
            self.id = id
            self.shard = shard

        ...

The glyph.redirect means that instead of returning the User object
directly, it should redirect to it's url. The client follows these
redirects automatically.

Even though the internals have changed, the names haven't, so the client
works as ever::

    bob = server.find_user('bob')
    bob.messsage('lol', 'feels good man')

Underneath all this - glyph maps all of this to http::

    # by default, a server returns an object with a bunch
    # of methods that redirect to the mapped obejcts

    server = glyph.get('http://server/')

    # in this case, it will have an attribute 'find_user'
    # find user is a special sort of object - a form
    # it has a url, method and arguments attached.


    # when we call server.find_user(...), it submits that form
    # find_user redirects to a url for User(bob_id, cluster_id)
    
    bob = server.find_user('bob')

    # each object is mapped to a url, which contains the internal state
    # of the object - i.e /User/?id=bob_id&cluster=cluster_id

    # the server is stateless - a new User object is created
    # for each request that comes in, before destroying it.

    # similarly, methods are mapped to a url too 
    # bob.message is a form pointing to /User/message?id=bo_id&cluster=cluster_id
    
    bob.messsage('lol', 'feels good man')


Although glyph maps urls to objects on the server side, these urls are
opaque to the client - the server is free to change them to point to
other objects, or to add new internal state without breaking the client.

Client code doesn't need to know how to construct requests, or store all 
of the state needed to make requests - the server tells it, rather than
the programmer.

The server is stateless - the state of the objects is encapsulated
in the links & forms. 

glyph now has large file support. wrap a file handle in glyph.blob,
and pass it around. on the server side, large blobs are written
to temporary files

internals
=========

glyph on the server end has four  major parts - a router, a mapper, a handler, and
a resource.

router - looks at url prefix, finds a resource class to use
mapper - associated with a class, it creates an instance to use
handler - given an instance, handles mapping the deserialization and serialization of the request
resource - the bit that actually services the request


the ruby client is currently the simplest, and the python client
has a lot more code for more generic http services.
