glyph-rpc
---------
it is like json-rpc with callbacks.

glyph is a client and server library for getting an object from a server,
and calling methods on it using the callbacks provided by the server.
the server offers objects over http, where the url describes the resource 
and its state, and GETing an object returns any contents & callbacks for methods

glyph uses urls internally to track the state between requests, but
the server is free to change the mapping without breaking the client.
this allows glyph to provide duck-typing: clients do not care *what* 
kind of object is returned, as long as it has the right named methods.

as a result, glyph allows you to grow your api like you grow a website.

- glyph services can redirect/link to other services on other hosts
- new methods and resources can be added without breaking clients
- glyph can take advantage of http tools like caches and load-balancers

glyph tries to exploit http rather than simply tunnel requests over it.

overview
--------

* simple echo server code, running it
* connecting with the client, calling a method
* inspecting the contents of the reply

* urls are object id's - used to create/find resources at server
* callbacks are links and forms, 

* how it works: router, mapper, resource
    - router
        attach resource classes to url prefixes
        on request, finds resource and its mapper
        uses the mapper to handle the request
    - mappers
        maps http <-> resource class
        url query string is the resource state
        make a resource to handle this request,
        and dispatch to a method
        adds callbacks to 
    - resources
        have an index() method that returns contents
        are created per request - represent a handle
        to some state at the server.

* configuration server?

serialization
-------------
the serialization format is an extension of bencoding (from bittorrent). 
it is not language specific, json-alike with a few more convieniences.

historical reasons mandated the support of bytestrings & unicode data, 
and existing formats (xml/json) required clumsy workarounds. it works
but i'm not proud to reinvent another wheel.


json like vocabulary
    - unicode -> u<len bytes>:<utf-8 string>
    - dict -> d<key><value><key><value>....e - sorted ascending by key
    - list -> l<item><item><item><item>....e
    - float -> f<len>:<float in hex - c99 hexadecimal literal format>
    - int -> i<number as text>e
    - true -> T
    - false -> F
    - none -> N
additonal datatypes
    - byte str -> s<len bytes>:<string>
    - datetime -> D%Y-%m-%dT%H:%M:%S.%f
xml like vocabulary
    - node -> N<name item><attr item><children item>
      an object with a name, attributes and children
      attributes is nominally a dict.  children nominally list
    - extension -> X<item><item><item>
      like a node, but contains hyperlinks.

todo: timezones, periods?
todo: standard behaviour on duplicate keys

expect some tweaks

history
-------
glyph evolved from trying to connect processes together, after some bad experiences
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


status
------

notable omissions:
    html/json/xml output
    content type overriding
    authentication handling



