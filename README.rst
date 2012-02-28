hate
----

hate is a python client/server library.  use it to glue things together.

(n.b. although hate is written in python, the protocol is not tied to it.)

the server turns objects into something like json* with callbacks. 

the client uses the callbacks from the server, as opposed to hardcoding a request

(note: may not resemble json when serialized)

not all of it is ready yet. check the examples to see what works.

example
-------
on the client::

    root = hate.get('http://...')
    
    mailbox = root.login(user, pass)

    mailbox.send('hjalp@cyberdog',subject, message)

    print mailbox.length(), mailbox.user


on the server::

    r = hate.Router() # a wsgi app

    @r.default()
    class Root(hate.r):
        def login(self, username, password):
            ...
            return Mailbox(user)
    @r.add()
    class Mailbox(hate.r):
        def __init__(self, user):
                self.user = user
        def inbox(self):
            ...
        def length(self):
            return ....
        def send(self, to, subject, message):
            ...


how it works
------------

the initial hate.get() gets a serialization of a Root instance. 
it has callbacks and attributes. these callbacks map to methods at the server,
and they can return other resources or json-like data.

at the server side, the  Root, Mailbox objects are transient. For each request the
server constructs a new instance to handle it, and deletes it afterwards. 

however, the callbacks know enough to reconstruct the object 
for subsequent requests. this means no in-place update of remote-objects.

under the covers, the serialization of an object is much like a webpage.
it has some data fields, but also contains forms. these forms are a callback to a 
particular method on the resource, along with the arguments needed.

the url is like a constructor of a resource. the path maps to the class 
(and possibly method to invoke), and the query arguments map to the
constructor arguments. 

in effect: the server is like a web server, and the client is like a screen scraper.

why hate?
---------
unlike other rpc systems where compiling service descriptions, or custom code 
is necessary for making requests, the server describes the object to the client,
using forms explain how to make requests.

this allows hate to provide duck-typing: clients do not care *what* 
kind of object is returned, as long as it has the right methods.

the server is now free to change where forms point to.  as a result,
hate allows you to grow your api like you grow a website.

- hate services can redirect/link to other services on other hosts
- new methods and resources can be added without breaking clients
- take advantage of http tools like caches and load-balancers

history
-------
hate evolved from trying to connect processes together, after some bad experiences
with message queues exploding. http was known and loved throughout the company, 
and yet another ad-hoc rpc system was born.  

in the beginning, there was JSON and POST, and it mostly worked with the notable exception of UnicodeDecodeError.
it didn't last very long. 8-bit data was a hard requirement, and so bencoding was used instead, with
a small change to handle utf-8 data as well as bytes.

we had a simple server stub that bound methods to urls and client code would call POST(url, {args}).
and we passed a bunch of urls around to sub-processes in order for them to report things. 
although we had not hard coded urls into the system, the api was still rigid. adding a new method
required passing in yet another url, or crafting urls per-request with client side logic. 

instead of passing around urls and writing stubs to use them each time, we figured we could pass around links and forms,
which would *know* how to call the api, and it would fetch these *from* the api server itself.
the urls contain enough information to make the call on the server end and are opaque to the client.

we've needed to change the api numerous times since then. adding new methods doesn't break old clients.
adding new state to the server doesn't break clients. using links and forms to interact with services is pleasant to
use for the client, and flexible for the server.

of all the terrible code i've written, this worked out pretty well so far.

hyperglyph
----------
the serialization format, hyperglyph, is an extension of bittorrent's bencoding. it is not language specific
and contains a simple vocabulary of data - json with a few more convieniences.

unfortunately; existing serialization formats don't cover links, forms and 8-bit data.
    - json is nice but fucked up unicode support. no binary support. no date support.
      can't do web like thinks - hyperlinks - no form support. no link support 
    - xml can't handle binary data nicely.and html5 is clunky for dicts, lists, times, booleans.

if you know of one please tell me, yet another ad-hoc format is a constant embarassment.

to mitigate the shame of writing my own serialization format, at least the implementation is relatively simple

json like vocabulary
    - unicode -> u<len>:<utf-8 string>
    - dict -> d<key><value><key><value>....e
    - list -> l<item><item><item><item>....e
    - float -> f<len>:<float in hex>
    - num -> i<number>e
    - true -> T
    - false -> F
    - none -> N
additonal datatypes
    - byte str -> s<len>:<string>
    - datetime -> D%Y-%m-%dT%H:%M:%S.%f
xml like vocabulary
    - node -> N<name item><attr item><children item>
      an object with a name, attributes and children
      attributes is nominally a dict.  children nominally list
    - extension -> X<item><item><item>
      like a node, but contains hyperlinks.

todo: timezones, periods?


status
------

notable omissions:
    html/json/xml output
    content type overriding
    authentication handling



