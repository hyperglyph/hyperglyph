""" resource.py

contains Resource, Mapper and Router
"""

from urllib import quote_plus, unquote_plus
from uuid import uuid4 


from werkzeug.wrappers import Request, Response
from werkzeug.exceptions import HTTPException, NotFound, BadRequest, NotImplemented, MethodNotAllowed
from werkzeug.utils import redirect as Redirect


from .data import CONTENT_TYPE, dump, parse, get, form, link, node, embed, ismethod, methodargs

"""
- router # moved to server.py
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
    
    url is roughly
        /ClassName/
        /ClassName/?instance-state
        /ClassName/method?instance state

    instance state for transient resources is
        a serialize dict of the class's constructor args
        from the instance dict

    posting /ClassName/ with args
        creates c = Class(**args)
        redirects to c 

    getting /ClassName/?args
        creates an index of the instance of Class
        a glyph.node() with attributes

"""

VERBS = set(("GET", "POST", "PUT","DELETE","PATCH",))

class BaseResource(object):
    """ An abstract resource to be served. Contains a mapper attribute __glyph__,
    which contains a mapper class to use for this resource,
    """
    __glyph__ = None

    def GET(self):
        """ Generate a glyph-node that contains 
            the object attributes and methods
        """
        page = dict()
        page.update(make_controls(self))
        page.update(self.index())
        return node(self.__class__.__name__, attributes=page)

    def index(self):
        return dict((k,v) for k,v in self.__dict__.items() if not k.startswith('_'))


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

    """ How post data is handled """
    @staticmethod
    def parse(data):
        return parse(data)
    
    @staticmethod
    def dump(data, resolver):
        return CONTENT_TYPE, dump(data, resolver)

    """ How query strings are handled. """
    @staticmethod
    def dump_query(d):
        """ transform a dict into a query string """
        return quote_plus(dump(d)) if d else ''

    @staticmethod
    def parse_query(query):
        """ turn a query string into a dict """
        return parse(unquote_plus(query)) if query else {}

    def handle(self,request, router):
        path = request.path[1:].split('/')
        verb = request.method.upper()

        if len(path) > 1 and path[1]:
            attr_name = path[1]
        else:
            attr_name = verb

        try:
            if len(path) > 1:
                args = self.parse_query(request.query_string)
                obj = self.get_instance(args)
                attr = getattr(obj, attr_name)
            else:
                attr = self.default_method(verb)
        except StandardError:
            raise BadRequest()
            

        if verb == 'GET' and ResourceMethod.is_safe(attr):
            result = attr()
        elif verb == 'POST' and not ResourceMethod.is_safe(attr): 
            try:
                data = ResourceMethod.parse(attr, request.data) if request.data else {}
            except StandardError:
                raise BadRequest()
            result =attr(**data)
        else:
            raise MethodNotAllowed()

        if ResourceMethod.is_redirect(attr) and isinstance(result, BaseResource):
            return Redirect(router.url(result), code=ResourceMethod.redirect_code(attr))
        else:
            content_type, result = ResourceMethod.dump(attr, result, router.url)
            return Response(result, content_type=content_type)

    def default_method(self, verb):
        if verb in VERBS:
            return getattr(self, verb)
        else:
            raise BadRequest()

    def url(self, r):
        """ return a url string that reflects this resource:
            can be a resource class, instance or method
        """
        if isinstance(r, self.cls):
            return "/%s/?%s"%(self.prefix, self.dump_query(self.get_repr(r)))
        elif isinstance(r, type) and issubclass(r, self.cls):
                return '/%s'%self.prefix
        elif ismethod(r, self.cls):
                return "/%s/%s/?%s"%(self.prefix, r.im_func.__name__, self.dump_query(self.get_repr(r.im_self)))
        raise LookupError()


    """ Abstract methods for creating, finding a resource, and getting the representation
    of a resource, to embed in the url """

    def get_instance(self, representation):
        raise NotImplemented()

    def get_repr(self, resource):
        """ return the representation of the state of the resource as a dict """
        raise NotImplemented()


class ResourceMethod(object):   
    """ Represents the capabilities of methods on resources, used by the mapper
        to determine how to handle requests
    """
    SAFE=False
    INLINE=False
    EXPIRES=False
    REDIRECT=False
    def __init__(self, resourcemethod=None):
        if resourcemethod:
            self.safe=resourcemethod.safe
            self.inline=resourcemethod.inline
            self.expires=resourcemethod.expires
        else:
            self.safe=self.SAFE
            self.inline=self.INLINE
            self.redirect=self.REDIRECT

    @staticmethod
    def parse(resource, data):
        return parse(data)
    
    @staticmethod
    def dump(resource, data, resolver):
        return CONTENT_TYPE, dump(data, resolver)

    @classmethod
    def is_safe(cls, m):
        try:
            return m.__glyph_method__.safe
        except StandardError:
            if m.__name__ == 'GET':
                return True
            return cls.SAFE

    @classmethod
    def is_inline(cls, m):
        try:
            return m.__glyph_method__.inline
        except StandardError:
            return cls.INLINE

    @classmethod
    def is_redirect(cls, m):
        try:
            return m.__glyph_method__.redirect
        except StandardError:
            return cls.REDIRECT
    @staticmethod
    def redirect_code(self):
        return 303

    @classmethod
    def make_link(cls, m):
        if cls.is_safe(m):
            if cls.is_inline(m):
                return embed(m,content=m())
            else:
                return link(m)
        else:
            return form(m)

def make_method_mapper(fn):
    if not hasattr(fn, '__glyph_method__'):
        fn.__glyph_method__ = ResourceMethod() 
    return fn.__glyph_method__


def redirect():
    def _decorate(fn):
        m = make_method_mapper(fn)
        m.redirect=True
        return fn
    return _decorate

def safe(inline=False):
    def _decorate(fn):
        m = make_method_mapper(fn)
        m.safe=True
        m.inline=inline
        return fn
    return _decorate

def inline():
    return safe(inline=True)

""" Transient Resources

When a request arrives, the mapper constructs a new instance of the resource,
using the query string to construct it. 

when you link to a resource instance, the link contains the state of the resource
encoded in the query string

"""
            
class TransientMapper(BaseMapper):  
    @redirect()
    def POST(self, **args):
        return self.get_instance(args)

    def get_instance(self, args):
        return self.cls(**args)

    def get_repr(self, resource):
        repr = {}
        args = methodargs(resource.__init__)
        for k,v in resource.__dict__.items():
            if k in args:
                repr[k] = v
        
        return  repr

class Resource(BaseResource):
    __glyph__ = TransientMapper


""" Persistent Resources """
            
class PersistentMapper(BaseMapper):  
    def __init__(self, prefix, cls):
        BaseMapper.__init__(self, prefix, cls)
        self.instances = {}
        self.identifiers = {}

    @redirect()
    def POST(self, **args):
        instance = self.cls(**args)
        uuid = str(uuid4())
        self.instances[uuid] = instance
        self.identifiers[instance] = uuid
        return instance

    def get_instance(self, uuid):
        return self.instances[uuid]

    def get_repr(self, instance):
        if instance not in self.identifiers:
            uuid = str(uuid4())
            self.instances[uuid] = instance
            self.identifiers[instance] = uuid
        else:
            uuid = self.identifiers[instance]
        return uuid

class PersistentResource(BaseResource):
    __glyph__ = PersistentMapper


def get_mapper(obj, name):
    """ return the mapper for this object, with a given name"""
    if hasattr(obj, '__glyph__') and issubclass(obj.__glyph__, BaseMapper):
        return obj.__glyph__(name, obj)
    raise StandardError('no mapper for object')

def make_controls(resource):
    forms = {}
    for m in dir(resource.__class__):
        if not m.startswith('_') and m not in VERBS:
            cls_attr = getattr(resource.__class__ ,m)
            if callable(cls_attr):
                ins_attr = getattr(resource,m)
                if hasattr(ins_attr, 'func_code'):
                    forms[m] = ResourceMethod.make_link(ins_attr)

    return forms
        

