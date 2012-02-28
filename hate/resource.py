import collections
import cgi
import re
import socket

from urllib import urlencode
from datetime import datetime
from pytz import utc

from werkzeug.wrappers import Request, Response
from werkzeug.exceptions import HTTPException

from hate.hyperglyph import CONTENT_TYPE, dump, parse, get, form, link, node


def ismethod(m, cls=None):
    return callable(m) and hasattr(m,'im_self') and (cls is None or isinstance(m.im_self, cls))

def methodargs(m):
    if ismethod(m):
        return m.func_code.co_varnames[1:]

def make_forms(resource):
    forms = {}
    for m in dir(resource.__class__):
        if not m.startswith('_'):
            cls_attr = getattr(resource.__class__ ,m)
            if isinstance(cls_attr, property):
                raise StandardError()
                page[m] = prop((resource,m))

            elif callable(cls_attr):
                ins_attr = getattr(resource,m)
                if hasattr(ins_attr, 'func_code'):
                    forms[m] = form(ins_attr, values=methodargs(ins_attr))
    return forms

class BaseMapper(object):
    def __init__(self, prefix, cls):
        self.prefix = prefix
        self.cls = cls

    def url(self, r):
        if isinstance(r, self.cls):
            return "/%s/?%s"%(self.prefix, urlencode(self.get_state(r)))
        elif isinstance(r, type) and issubclass(r, self.cls):
                return '/%s/'%self.prefix
        elif ismethod(r, self.cls):
                return "/%s/%s/?%s"%(self.prefix, r.im_func.__name__, urlencode(self.get_state(r.im_self)))


    def handle(self,request, router):
        path = request.path[1:].split('/')[1:]
        # todo throw nice errors here? bad request?
        obj = self.get_resource(request.args)
        # try/ 404 ?
        attr = 'index' if not path or not path[0] else path[0]

        attr  = getattr(obj, attr)

        method = request.method
        if method == 'GET' and (attr =='index' or getattr(attr, 'safe', False)):
            result = attr()
        elif method =='POST': # post is always ok!
            data = parse(request.data) if request.data else {}
            result =attr(**data)

        if isinstance(result, Resource):
            raise SeeOther(router.url(result))

        result = dump(result, router.url)

        return Response(result, content_type=CONTENT_TYPE)


def safe():
    def _decorate(fn):
        fn.safe = True
        return fn
    return _decorate

class TransientMapper(BaseMapper):
    def get_resource(self, args):
        """ given the representation of the state of a resource, return a resource instance """
        query = dict(args.items())
        return self.cls(**query)

    def get_state(self, resource):
        """ return the representation of the state of the resource as a dict """
        return resource.__dict__



class Resource(object):
    __hate__ = TransientMapper

    @safe()
    def index(self):
        page = dict((k,v) for k,v in self.__dict__.items() if not k.startswith('_'))
        page.update(make_forms(self))
        return node(self.__class__.__name__, attributes=page)
        
def get_mapper(obj, name):
    if hasattr(obj, '__hate__') and issubclass(obj.__hate__, BaseMapper):
        return obj.__hate__(name, obj)
    raise StandardError('no mapper for object')

class SeeOther(HTTPException):
    code = 303
    description = ''
    def __init__(self, url):
        self.url = url
        HTTPException.__init__(self)
    def get_headers(self, environ):
        return [('Location', self.url)]

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
        elif isinstance(r, Resource):
            return self.mappers[r.__class__].url(r)
        elif (isinstance(r, type) and issubclass(r, Resource)):
            return self.mappers[r].url(r)
        elif ismethod(r, Resource):
            return self.mappers[r.im_class].url(r)

        raise StandardError('cant encode',r )

    def add(self):
        return self.register

    def default(self):
        return lambda obj: self.register(obj, default=True)
