hate
----

hate is an client/server library, that behaves nicely with http,
it aims to let you grow your api without breaking clients.

caveat emptor: it is a work in progress, based on some earlier experiments at work.


example
-------

on the server::
    class Root(hate.r):
        def login(self, username, password):
            ...
            raise Redirect(Mailbox(user))
            
    class Mailbox(hate.r):
        def __init__(self, user):
                self.user = user
        def inbox(self):
            ...
        def length(self):
            return ....
        def send(self, to, subject, message):
            ...

on the client::
    mailbox = hate.get('http://...').login(user, pass)

    mailbox.send('hjalp@cyberdog',subject, message)

    print mailbox.length(), mailbox.user


how it works
------------
the server is a web server, Mailbox is mapped to a url.
When the client GETs the mailbox, it gets serialized
the object contains the instance __dict__ values
and the methods are transformed into forms.

the client is a screen-scraper, it reads a page and transforms 
it back into an object. forms can be invoked on the page, like
a method call: page.name(args)

when the client POSTs a form, the url is mapped back 
to the object and method and invoked with the POST data.
methods can return data, or redirect to other objects.
data can be lists, dicts, str, unicode, 
and can also include links and forms.

the key idea
------------

instead of sharing lists of method names, service description
languages, or urls ahead of time, links and forms drive the 
interaction.

the server is free to change where links point to, and to add new methods,
without changing client code. 


why hate?
---------
it's often easier to scrape a website than use the api
    - they often change links more than form names and link names
    - slicing through html is often not much more work than detangling xml
    - using it in a browser is *self documenting* - very easy to discover bits of the api
    - all requests look the same - you only need one library for all websites
        
apis are harder to grow than websites
    - load balancing can be hard (the request/responses are stateful)
    - caching can be hard to add, and must be done ad-hoc in client
    - versioning is hard
        
rpc systems require too much hard coding
    - url construction, request formatting, often ad-hoc. 
    - often requires service-specific client libs, or they must be generated.

existing serialization formats don't cover links, forms and 8-bit data.
    - json is nice but fucked up unicode support. no binary support. no date support.
      can't do web like thinks - hyperlinks - no form support. no link support 
    - xml can't handle binary data nicely.and html5 is clunky for dicts, lists, times, booleans.
    - if you know of one please tell me, yet another ad-hoc format is a constant embarassment.
    
snapshotting/archiving information is hard
    - can't explore api, don't know what is safe to crawl
    


history
-------
hate evolved from experiments at work with connecting the various components together. we'd had
some bad experiences with message queues exploding, so we avoided brokers. we knew and loved 
http, so we embraced it. 

in the beginning, we used json and POST, and it mostly worked, except for UnicodeDecodeErrors.
we wanted to send 8-bit data, but the json only supports unicode. so I took bencoding as inspiration
and hacked up an implementation, and it worked.

we had a simple server stub that bound methods to urls, client code would call POST(url, {args})
and we passed a bunch of urls around to sub-processes in order for them to report things. 

we found that although we had not hard coded urls into the system, the api was still rigid. adding a new method
required passing in yet another url, or crafting urls per-request with client side logic. 

instead of passing around urls and writing stubs to use them each time, we figured we could pass around links and forms,
which would *know* how to call the api, and it would fetch these *from* the api server itself.
the urls contain enough information to make the call on the server end and they are opaque to the client.

it worked out. we've needed to change the api numerous times since then. adding new methods doesn't break old clients.
adding new state to the server doesn't break clients. using links and forms to interact with services is pleasant to
use for the client, and flexible for the server.

hyperglyph
----------
the serialization format, hyperglyph, is an extension of bittorrent's bencoding. it is not language specific
and contains a simple vocabulary of data - json with a few more convieniences.

i'm embarrased by needing my own serialization format, but the implementation is relatively simple

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

hate is an http object mapper:
    - mapper (done):
        - maps classes & objects to pages at urls, GETing them returns state & forms which POST
        to methods on that class
        - some objects are per-request, some are persistent
        - urls and hyperlinks are handled for you
                
    - transient pages- instance per request (done)
        - urls are constructors - the path says which object, and the query string are the parameters.
        - GETting a url returns the object contents, and forms for each method
        - forms are built from the method signature, and they can be annotated with decorators
        - objects are constructed for each request, and disposed afterwards.
        
    - persistent pages:
        - some objects need to persist between requests, and can expire eventually
        - the mapper keeps a reference to it, and maps a *unique* url to this object.
        - have an expiry date
        
        
    - serialization: hencoding (partially done)
        - data serialized using bencode/netstrings alike formatting.
        - basic: boolean, numbers, lists, dicts, unicode (utf-8), isodatetimes, bytestrings
        - generic 'object type' - has attributes and children objects
        - hypermedia objects/affordances: i.e a/link/form/embed - 
        
    - opt-in/opt-out (partially)
        - decorators work on classes & methods ?
        - can use decorators to *describe* methods on objects as safe/cacheable
        - can override GET behaviour
        - can customise inputs/responses with specific content-types
        - can return custom urls          

    -browser-debugger
        
    -collections:
        - some pages have relations to other pages, in a series.
        - inlining? - treat them as methods (like forms) but no underlying call ?


add links to hypermedia design and actions vs entities.



