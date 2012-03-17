""" resource.py

contains Resource, Mapper and Router
"""

from urllib import quote_plus, unquote_plus


from werkzeug.wrappers import Request, Response
from werkzeug.exceptions import HTTPException, NotFound, BadRequest, NotImplemented, MethodNotAllowed
from werkzeug.utils import redirect as Redirect

from ..data import CONTENT_TYPE, dump, parse, get, form, link, node, embed, ismethod, methodargs

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

def get_mapper(obj, name):
    """ return the mapper for this object, with a given name"""
    if hasattr(obj, '__glyph__') and issubclass(obj.__glyph__, BaseMapper):
        return obj.__glyph__(name, obj)
    raise StandardError('no mapper for object')

class BaseMapper(object):
    """ The base mapper - bound to a class and a prefix, handles requests
    from the router, and finds/creates a resource to handle it.

    This handles the verb mapping part of http, as well as the serializing/
    deserializing content. It also maps methods to urls, as well as object
    state representation.
    """

    def __init__(self, prefix, res):
        self.prefix = prefix
        self.res = res

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
        return Handler.call(self.res, request, router)

    def url(self, r):
        """ return a url string that reflects this resource:
            can be a resource class, instance or method
        """
        if isinstance(r, basestring):
            return r
        elif r is self.res:
            return '/%s'%self.prefix

        raise LookupError()

class ClassMapper(BaseMapper):
    def handle(self,request, router):
        path = request.path[1:].split('/')
        verb = request.method.upper()

        try:
            if len(path) > 1: 
                # if we are mapping to an instance
                attr_name = path[1] if path[1] else verb
                args = self.parse_query(request.query_string)
                obj = self.get_instance(args)

                # find the method to call
                attr = getattr(obj, attr_name)

            else:
                # no instance found, use default handler
                attr = self.default_method(verb)

        except StandardError:
            raise BadRequest()

        return Handler.call(attr, request, router)

    def default_method(self, verb):
        try:
            return getattr(self, verb)
        except:
            raise MethodNotAllowed()
    def url(self, r):
        """ return a url string that reflects this resource:
            can be a resource class, instance or method
        """
        if isinstance(r, self.res):
            return "/%s/?%s"%(self.prefix, self.dump_query(self.get_repr(r)))
        elif isinstance(r, type) and issubclass(r, self.res):
                return '/%s'%self.prefix
        elif ismethod(r, self.res):
                return "/%s/%s?%s"%(self.prefix, r.im_func.__name__, self.dump_query(self.get_repr(r.im_self)))
        else:
            return BaseMapper.url(self, r)

    """ Abstract methods for creating, finding a resource, and getting the representation
    of a resource, to embed in the url """

    def get_instance(self, representation):
        raise NotImplemented()

    def get_repr(self, resource):
        """ return the representation of the state of the resource as a dict """
        raise NotImplemented()



class Handler(object):   
    """ Represents the capabilities of methods on resources, used by the mapper
        to determine how to handle requests
    """
    SAFE=False
    INLINE=False
    EXPIRES=False
    REDIRECT=None
    def __init__(self, handler=None):
        if handler:
            self.safe=handler.safe
            self.inline=handler.inline
            self.expires=handler.expires
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
            return m.__glyph_method__.redirect is not None
        except StandardError:
            return cls.REDIRECT

    @staticmethod
    def redirect_code(m):
        return m.__glyph_method__.redirect

    @classmethod
    def make_link(cls, m):
        if cls.is_safe(m):
            if cls.is_inline(m):
                return embed(m,content=m())
            else:
                return link(m)
        else:
            return form(m)

    @classmethod
    def call(cls, attr, request, router):
        verb = request.method
        if verb == 'GET' and cls.is_safe(attr):
            result = attr()
        elif verb == 'POST' and not cls.is_safe(attr): 
            try:
                data = cls.parse(attr, request.data) if request.data else {}
            except StandardError:
                raise BadRequest()
            result =attr(**data)
        else:
            raise MethodNotAllowed()

        if result is None:
            return Response('', status='204 None')

        elif cls.is_redirect(attr) and isinstance(result, BaseResource):
            return Redirect(router.url(result), code=cls.redirect_code(attr))
        else:
            content_type, result = cls.dump(attr, result, router.url)
            return Response(result, content_type=content_type)

def make_controls(resource):
    forms = {}
    for m in dir(resource.__class__):
        if not m.startswith('_') and m not in VERBS:
            cls_attr = getattr(resource.__class__ ,m)
            if callable(cls_attr):
                ins_attr = getattr(resource,m)
                if hasattr(ins_attr, 'func_code'):
                    forms[m] = Handler.make_link(ins_attr)

    return forms


def make_handler(fn):
    if not hasattr(fn, '__glyph_method__'):
        fn.__glyph_method__ = Handler() 
    return fn.__glyph_method__


def redirect(code=303):
    def _decorate(fn):
        m = make_handler(fn)
        m.redirect=code
        return fn
    return _decorate

def safe(inline=False):
    def _decorate(fn):
        m = make_handler(fn)
        m.safe=True
        m.inline=inline
        return fn
    return _decorate

def inline():
    return safe(inline=True)

