import types
import traceback

from urllib import quote_plus, unquote_plus


from werkzeug.wrappers import Request, Response
from werkzeug.exceptions import HTTPException, NotFound, BadRequest, NotImplemented, MethodNotAllowed
from werkzeug.utils import redirect as Redirect

from ..data import CONTENT_TYPE, dump, parse, get, form, link, robj, embedlink, ismethod, methodargs

VERBS = set(("GET", "POST", "PUT","DELETE","PATCH",))
from .handler import Handler

def make_controls(resource):
    forms = {}
    for m in dir(resource.__class__):
        cls_attr = getattr(resource.__class__ ,m)
        ins_attr = getattr(resource,m)
        if cls_attr == ins_attr:
            # schenanigans
            # classmethods are going to be weird. staticmethods weirder
            # ignore them for now
            continue
            

        m = unicode(m)
        if m not in VERBS and Handler.is_visible(ins_attr, name=m):
            if isinstance(cls_attr, property):
                # just inline the property
                forms[m] = ins_attr
            elif callable(cls_attr):
                # but if it is a method or similar, make a link/form
                if hasattr(ins_attr, 'func_code'):
                    forms[m] = Handler.make_link(ins_attr)

    return forms


class BaseResource(object):
    """ An abstract resource to be served. Contains a mapper attribute __glyph__,
    which contains a mapper class to use for this resource,
    """
    __glyph__ = None

    def GET(self):
        return self
def get_mapper(obj, name):
    """ return the mapper for this object, with a given name"""
    if hasattr(obj, '__glyph__') and issubclass(obj.__glyph__, BaseMapper):
        return obj.__glyph__(name, obj)
    elif isinstance(obj, types.FunctionType):
        return BaseMapper(name, obj)
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

    def inline(self,resource):
        return Handler.make_link(resource)

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
        path = request.path.split(self.prefix)[1]
        verb = request.method.upper() 
        if 'Method' in request.headers:
            verb = request.headers['Method']

        try:
            if path:
                # if we are mapping to an instance
                attr_name = path[1:] if path [1:]  else verb
                args = self.parse_query(request.query_string)
                obj = self.get_instance(args)

                # find the method to call
                attr = getattr(obj, attr_name)

            else:
                # no instance found, use default handler
                attr = self.default_method(verb)

        except StandardError as e:
            router.log_error(e, traceback.format_exc())
            raise BadRequest()

        return Handler.call(attr, request, router)

    def inline(self,resource):
        if isinstance(resource, BaseResource):
            return self.inline_resource(resource)
        else:
            return Handler.make_link(resource)

        """ Generate a glyph-node that contains 
            the object attributes and methods
        """
    def inline_resource(self, resource):
        page = dict()
        page.update(make_controls(resource))
        page.update(self.index(resource))
        return robj(resource, page)

    def index(self, resource):
        return dict((unicode(k),v) for k,v in resource.__dict__.items() if not k.startswith('_'))


    def default_method(self, verb):
        if verb not in VERBS:
            raise MethodNotAllowed(verb)
        try:
            return getattr(self, verb)
        except:
            raise MethodNotAllowed()

    def url(self, r):
        """ return a url string that reflects this resource:
            can be a resource class, instance or method
        """
        if isinstance(r, self.res):
            return u"/%s/?%s"%(self.prefix, self.dump_query(self.get_repr(r)))
        elif isinstance(r, type) and issubclass(r, self.res):
                return u'/%s'%self.prefix
        elif ismethod(r, self.res):
                return u"/%s/%s?%s"%(self.prefix, r.im_func.__name__, self.dump_query(self.get_repr(r.im_self)))
        else:
            return BaseMapper.url(self, r)

    """ Abstract methods for creating, finding a resource, and getting the representation
    of a resource, to embed in the url """

    def get_instance(self, representation):
        raise NotImplemented()

    def get_repr(self, resource):
        """ return the representation of the state of the resource as a dict """
        raise NotImplemented()



