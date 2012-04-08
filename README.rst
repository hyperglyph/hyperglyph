glyph-rpc
---------
glyph-rpc makes minature websites for your objects, so you can grow your api
like you grow a website:

- new methods and objects can be added without breaking clients
- glyph services can redirect/link to other services on other hosts
- glyph can take advantage of http tools like caches and load-balancers

glyph-rpc tries to exploit http rather than simply tunnel requests over it.

example
-------

The server:
    import glyph

    r = glyph.Router() # a wsgi application

    @r.add()
    def hello()
        return "Hello World"

    s = glyph.Server(r)
    s.start()

The client:
    import glyph

    server = glyph.get('http://server/')

    print server.hello()

There is no stub for the client, just the library. 

Adding a new function is simple:
    @r.add()
    def goodbye(name):
        return "Goodbye " + name

Or change the functions a little:
    @r.add()
    def hello(name="World"):
        return "Hello "+name

The client still works, without changes:
    print server.hello()

with very little changes to call new methods:
    print server.hello('dave')
    print server.goodbye('dave')

functions can return lists, dicts, sets, byte strings, unicode,
dates, booleans, ints & floats:
    @r.add()
    def woo():
        return [1,True, None, False, "a",u"b"]

functions can even return other functions that are mapped,
through redirection:

    @r.add()
    @glyph.redirect()
    def greeting(lang="en"):
        if lang == "en":
            return hello

the client doesn't care: 
    greet = client.greeting()

    print greet()
    

glyph can map objects too:
    @r.add()
    @glyph.redirect()
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

and the client can get a User and find details:
    bob = server.find_user('bob')
    bob.messsage('lol', 'feels good man')

like before, new methods can be added without breaking old clients.
unlike before, we can change object internals:

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

Even though the internals have changed, the names haven't, so the client
works as ever:

    bob = server.find_user('bob')
    bob.messsage('lol', 'feels good man')

underneath all this - glyph maps all of this to http:
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

    # similarly, methods are mapped to a url too 
    # bob.message is a form pointing to /User/message?id=bo_id&cluster=cluster_id
    
    bob.messsage('lol', 'feels good man')


although glyph maps urls to objects on the server side, these urls are
opaque to the client - the server is free to change them to point to
other objects, or to add new internal state without breaking the client.

Client code doesn't need to know how to construct requests, or store all 
of the state needed to make requests - the server tells it, rather than
the programmer.


