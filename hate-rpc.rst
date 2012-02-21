hate rpc - websites for robots
 
a well behaved rpc (request/response) service for the web.

existing problems with web api systems:
    - it's often easier to scrape a website than use the api
        - they often change links more than form names and link names
        - slicing through html is often not much more work than detangling xml
        - using it in a browser is *self documenting* - very easy to discover bits of the api
        - all requests look the same - you only need one library for all websites
        
    - layering: apis are harder to grow than websites - 
        - load balancing can be hard (the request/responses are stateful)
        - caching can be hard to add, and must be done ad-hoc
        
    - serialization formats aren't great
        - json
            - is nice but it has a few weird edge cases, and a few types missing.
                fucked up unicode support. no binary support. no date support.
            - can't do web like thinks - hyperlinks
                 no url support. no link support 
        
        - xml can't handle binary data nicely.
            - and html5 is clunky for dicts, lists, times, booleans.
        
        - custom mime types for everything is often getting it right in advance,
            even text fields can contain custom data
        
    - versioning is hard
        - manual labour - no help from services
        
    - 'restful' requires custom libraries 
        - each request is a snowflake

    - wsdl/soap
        - stack inconsistencies - code generation problems
        - versioning - schema inconsistencies
    
    - snapshotting/archiving information is hard
        - can't explore api, don't know what is safe to crawl
    
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

