""" resource.py

contains Resource, Mapper and Router

- router
   attach resource classes to url prefixes
   on request, finds resource and its mapper
   uses the mapper to handle the request

- mappers
    maps http <-> resource class
    url query string is the resource state
    make a resource to handle this request, and dispatch to a method
    special handling for index 
    deals with representing the state of an object in the url

- resources
    have an index() method that returns contents
    are created per request - represent a handle
    to some state at the serve
"""
from datetime import datetime
from pytz import utc
from urllib import quote_plus, unquote_plus

from werkzeug.wrappers import Request, Response
from werkzeug.exceptions import HTTPException

from .encoding import CONTENT_TYPE, dump, parse, get, form, link, node, embed, ismethod


class SeeOther(HTTPException):
    """ A werkzeug http exception for redirects """
    code = 303
    description = ''
    def __init__(self, url):
        self.url = url
        HTTPException.__init__(self)
    def get_headers(self, environ):
        return [('Location', self.url)]

class BaseResource(object):
    """ An abstract resource to be served. Contains a mapper attribute __glyph__,
    which contains a mapper class to use for this resource,
    """
    __glyph__ = None

    def index(self):
        raise StandardError('missing')



class BaseMapper(object):
    """ The base mapper - bound to a class and a prefix, handles requests
    from the router, and finds/creates a resource to handle it.

    This handles the verb mapping part of http, as well as the serializing/
    deserializing content. It also maps methods to urls, as well as object
    state representation.
    """

    def __init__(self, prefix, cls):
        self.prefix = prefix
        self.cls = cls


    def handle(self,request, router):
        """ handle a given request from a router:
            find the right resource:
                dispatch to a method 
            or
                create an index of the object,
                including forms for methods

        """
        # todo throw nice errors here? bad request?

        path = request.path[1:].split('/')[1:]
        attr_name = 'index' if not path or not path[0] else path[0]
        verb = request.method

        if attr_name == 'index' and  verb  == 'POST':
            # the object state is either in the post data
            args = self.parse(request.data) if request.data else {}
        else:
            # or in the query args
            args = self.parse_query(request.query_string)

        obj = self.get_resource(args)

        if attr_name == 'index':
            if verb == 'GET':
                result = self.index(obj)
                result = self.dump(result, router.url)
            else:
                # POSTing to the index redirects
                # to GETing it with the state in the query string
                raise SeeOther(router.url(obj))
        else:
            attr  = getattr(obj, attr_name)

            if verb == 'GET' and ResourceMethod.is_safe(attr):
                result = attr()
            elif verb == 'POST' and not ResourceMethod.is_safe(attr): 
                data = ResourceMethod.parse(attr, request.data) if request.data else {}
                result =attr(**data)
            else:
                raise StanardError('unhandled')

            if ResourceMethod.is_redirect(attr) and isinstance(result, BaseResource):
                raise SeeOther(router.url(result))

            result = dump(result, router.url)

        return Response(result, content_type=CONTENT_TYPE)

    def index(self, obj):
        """ Generate a glyph-node that contains 
            the object attributes and methods
        """
        page = dict()
        page.update(make_controls(obj))
        page.update(obj.index())
        return node(obj.__class__.__name__, attributes=page)

    def url(self, r):
        """ return a url string that reflects this resource:
            can be a resource class, instance or method
        """
        if isinstance(r, self.cls):
            return "/%s/?%s"%(self.prefix, self.get_query(r))
        elif isinstance(r, type) and issubclass(r, self.cls):
                return '/%s/'%self.prefix
        elif ismethod(r, self.cls):
                return "/%s/%s/?%s"%(self.prefix, r.im_func.__name__, self.get_query(r.im_self))


    @staticmethod
    def parse(data):
        return parse(data)
    
    @staticmethod
    def dump(data, resolver):
        return dump(data, resolver)

    def get_query(self, r):
        """ transform the state of a resource into a query string """
        s = self.get_state(r)
        return quote_plus(dump(s)) if s else ''

    def parse_query(self, query):
        """ turn a query string into a dict """
        return parse(unquote_plus(query)) if query else {}

""" Transient Resources

When a request arrives, the mapper constructs a new instance of the resource,
using the query string to construct it. 

when you link to a resource instance, the link contains the state of the resource
encoded in the query string

"""
            
class TransientMapper(BaseMapper):
    def get_resource(self, args):
        """ given the representation of the state of a resource, return a resource instance """
        return self.cls(**args)

    def get_state(self, resource):
        """ return the representation of the state of the resource as a dict """
        return resource.__dict__

class Resource(BaseResource):
    __glyph__ = TransientMapper

    def index(self):
        return dict((k,v) for k,v in self.__dict__.items() if not k.startswith('_'))


class ResourceMethod(object):   
    """ Represents the capabilities of methods on resources, used by the mapper
        to determine how to handle requests
    """
    SAFE=False
    INLINE=False
    EXPIRES=False
    REDIRECT=False
    def __init__(self, safe=SAFE, inline=INLINE, expires=EXPIRES, redirect=REDIRECT):
        self.safe=safe
        self.inline=inline
        self.expires=expires

    @staticmethod
    def parse(resource, data):
        return parse(data)
    
    @staticmethod
    def dump(resource, data, resolver):
        return dump(data, resolver)

    @classmethod
    def is_safe(cls, m):
        try:
            return m.__glyph_method__.safe
        except:
            return cls.SAFE

    @classmethod
    def is_inline(cls, m):
        try:
            return m.__glyph_method__.inline
        except:
            return cls.INLINE

    @classmethod
    def is_redirect(cls, m):
        try:
            return m.__glyph_method__.redirect
        except:
            return cls.REDIRECT

def get_mapper(obj, name):
    """ return the mapper for this object, with a given name"""
    if hasattr(obj, '__glyph__') and issubclass(obj.__glyph__, BaseMapper):
        return obj.__glyph__(name, obj)
    raise StandardError('no mapper for object')


class Router(object):
    def __init__(self):
        self.mappers = {}
        self.routes = {}
        self.default_path=''

    def __call__(self, environ, start_response):
        request = Request(environ)
        try:
            response = self.find_mapper(request.path).handle(request, self)
        except (StopIteration, GeneratorExit, SystemExit, KeyboardInterrupt):
            raise
        except HTTPException as r:
            response = r
        except Exception as e:
            import traceback;
            traceback.print_exc()
            response = Response(traceback.format_exc(), status='500 not ok')
        return response(environ, start_response)


    def find_mapper(self, path):
        if path == '/':
            raise SeeOther(self.default_path)
        path= path[1:].split('/')
        return  self.routes[path[0]]

    def register(self, obj, path=None, default=False):
        if path is None: 
            path = obj.__name__
        mapper = get_mapper(obj, path)
        self.routes[path] = mapper
        self.mappers[obj] = mapper
        if default:
            self.default_path=path
        return obj


    def url(self, r):
        if isinstance(r, basestring):
            return r
        elif isinstance(r, BaseResource):
            return self.mappers[r.__class__].url(r)
        elif (isinstance(r, type) and issubclass(r, BaseResource)):
            return self.mappers[r].url(r)
        elif ismethod(r, BaseResource):
            return self.mappers[r.im_class].url(r)

        raise StandardError('cant encode',r )

    def add(self):
        return self.register

    def default(self):
        return lambda obj: self.register(obj, default=True)

def make_controls(resource):
    forms = {}
    for m in dir(resource.__class__):
        if not m.startswith('_') and m != 'index':
            cls_attr = getattr(resource.__class__ ,m)
            if isinstance(cls_attr, property):
                raise StandardError()
                page[m] = prop((resource,m))

            elif callable(cls_attr):
                ins_attr = getattr(resource,m)
                if hasattr(ins_attr, 'func_code'):
                    if ResourceMethod.is_safe(cls_attr):
                        if ResourceMethod.is_inline(cls_attr):
                            forms[m] = embed(ins_attr,content=ins_attr())
                        else:
                            forms[m] = link(ins_attr)
                    else:
                        forms[m] = form(ins_attr)
    return forms
        
def make_method_mapper(fn):
    if not hasattr(fn, '__glyph_method__'):
        fn.__glyph_method__ = ResourceMethod() 
    return fn.__glyph_method__

def redirect(is_redirect=True):
    def _decorate(fn):
        m = make_method_mapper(fn)
        m.redirect=is_redirect
        return fn
    return _decorate

def safe(is_safe=True):
    def _decorate(fn):
        m = make_method_mapper(fn)
        m.safe=is_safe
        return fn
    return _decorate

def inline(is_inline=True):
    def _decorate(fn):
        m = make_method_mapper(fn)
        m.safe=is_inline
        m.inline=is_inline
        return fn

    return _decorate

