import collections
import cgi
import re
import socket

from urllib import urlencode
from datetime import datetime
from pytz import utc

from werkzeug.wrappers import Request, Response
from werkzeug.exceptions import HTTPException

from hate.hyperglyph import CONTENT_TYPE, dump, parse, get, Node, Extension

def node(name, attributes, children=None):
    return Node(name, attributes, children)

def form(url, method='POST',values=None):
    if callable(url) and hasattr(url, 'func_code'):
        values=url.func_code.co_varnames[1:]
    return Extension.make('form', {'method':method, 'url':url}, values)

def link(url, method='GET'):
    return Extension.make('link', {'method':method, 'url':url}, [])

def prop(url):
    return Extension.make('property', {'url':url}, [])

def page(resource):
    page = {}
    for k,v in resource.__dict__.items():
        if not k.startswith('_'):
            page[k] = v
    
    for m in dir(resource.__class__):
        if not m.startswith('_'):
            cls_attr = getattr(resource.__class__ ,m)
            if isinstance(cls_attr, property):
                raise StandardError()
                page[m] = prop((resource,m))

            elif callable:
                ins_attr = getattr(resource,m)
                if hasattr(ins_attr, 'func_code'):
                    page[m] = form(ins_attr)
    return node(resource.__class__.__name__, attributes=page)




class TransientMapper(object):
    def __init__(self, prefix, cls):
        self.prefix = prefix
        self.cls = cls

    def handle(self,request, resolver):
        method = request.method
        path = request.path[1:].split('/')[1:]
        data = request.data
        headers = request.headers

        if data:
            data = parse(data)
        else:
            data={}

        if path:
            path = path[0]
        print self.cls

        query = dict([(k,v[0]) for k,v in request.args.items()])
        obj = self.cls(**query)

        if path:
            r = getattr(obj, path)
            if method == 'GET' or method == 'HEAD' and hasattr(r,'GET'):
                result=r()
            elif method =='POST': # post is always ok!
                result =r(**data)
        else:
            if method == 'GET' or method == 'HEAD':
                result = page(obj)
            else:
                raise HTTPException('missing method '+repr(method))

        if isinstance(result, Resource):
            raise SeeOther(resolver(result))

        result = dump(result, resolver)
        return Response(result, content_type=CONTENT_TYPE)


class Resource(object):
    __hate__ = TransientMapper
    

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
        self.paths = {}
        self.mappers = {}
        self.default_path=''

    def __call__(self, environ, start_response):
        request = Request(environ)
        try:
            response = self.find_mapper(request).handle(request, self.url)
        except (StopIteration, GeneratorExit, SystemExit, KeyboardInterrupt):
            raise
        except HTTPException as r:
            response = r
        except Exception as e:
            import traceback;
            traceback.print_exc()
            response = Response(traceback.format_exc(), status='500 not ok')
        return response(environ, start_response)


    def find_mapper(self, request):
        if request.path == '/':
            raise SeeOther(self.default_path)
        path=request.path[1:].split('/')
        mapper = self.mappers[path[0]]
        return mapper

    def register(self, obj, path=None, default=False):
        if path is None: 
            path = obj.__name__
        mapper = obj.__hate__(path, obj)
        self.mappers[path] = mapper
        self.paths[obj] = path
        if default:
            self.default_path=path
        return obj

    def add(self):
        return self.register

    def default(self):
        return lambda obj: self.register(obj, default=True)

    def url(self, r):
        try:
            if isinstance(r, basestring):
                return r
            elif isinstance(r, Resource):
                return "/%s/?%s"%(self.paths[r.__class__], urlencode(r.__dict__))
            elif isinstance(r, type) and issubclass(r, Resource):
                return self.paths[r]
            elif callable(r) and hasattr(r,'im_self'):
                return "/%s/%s/?%s"%(self.paths[r.im_self.__class__], r.im_func.__name__, urlencode(r.im_self.__dict__))
        except:
            import traceback;
            traceback.print_exc()
            
        raise StandardError('cant encode')
