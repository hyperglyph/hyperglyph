import collections
import cgi
import re
import socket

from urllib import urlencode
from datetime import datetime
from pytz import utc

from werkzeug.wrappers import Request, Response

from hate.hyperglyph import CONTENT_TYPE, dump, parse, get, Node, Extension

def node(name, attributes, children=None):
    return Node(name, attributes, children)

def form(url, method='POST',values=()):
    return Extension.make('form', {'method':method, 'url':url}, values)

def link(url, method='GET'):
    return Extension.make('link', {'method':method, 'url':url}, [])

def page(resource):
    page = {}
    for k,v in resource.__dict__.items():
        if not k.startswith('_'):
            page[k] = v
    
    for m in resource.__class__.__dict__:
        if not m.startswith('_'):
            attr = getattr(resource,m)
            if hasattr(attr, 'func_code'):
                page[m] = form(attr, values=attr.func_code.co_varnames[1:])
    return node(resource.__class__.__name__, attributes=page)


class Redirect(BaseException):
    def __init__(self, url):
        self.url = url

class Resource(object):
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


        try:
            if path:
                r = getattr(self, path)
                if method == 'GET' or method == 'HEAD' and hasattr(r,'GET'):
                    result=r()
                elif method == 'DELETE' and hasattr(r,'DELETE'):
                    result=r()
                elif method =='POST': # post is always ok!
                    result =r(**data)
                elif method =='PUT' and hasattr(r, 'PUT'):
                    result=r(data)
                else:
                    raise CustomResponse('missing method '+repr(method))
            else:
                if method == 'GET' or method == 'HEAD':
                    result = self.get()
                elif method == 'DELETE':
                    result = self.delete()
                elif method =='POST':
                    result = self.post(**data)
                elif method =='PUT':
                    result = self.put(data)
                else:
                    raise CustomResponse('missing method '+repr(method))
        except Redirect as r:
            raise SeeOther(resolver(r.url))
        
        if isinstance(result, Resource):
            raise SeeOther(resolver(result))

        result = dump(result, resolver)
        return Response(result, content_type=CONTENT_TYPE)

    def get(self):
        return page(self)

    def post(self, data):
        pass

    def put(self, data):
        pass

    def delete(self):
        pass
    
def GET():
    def _decorate(fn):
        fn.GET=True
        return fn
    return _decorate

def POST():
    def _decorate(fn):
        fn.POST=True
        return fn
    return _decorate

def PUT():
    def _decorate(fn):
        fn.PUT=True
        return fn
    return _decorate

def DELETE():
    def _decorate(fn):
        fn.DELETE=True
        return fn
    return _decorate

class CustomResponse(BaseException):
    def __init__(self, status, text='', headers=()):
        self.text=text
        self.status=status
        self.headers=headers
    def response(self):
        return Response(self.text, status=self.status, headers=self.headers)

class ServerError(CustomResponse):
    def __init__(self, reason):
        CustomResponse.__init__(self, status='500 error', text=reason)

class SeeOther(CustomResponse):
    def __init__(self, url):
        CustomResponse.__init__(self, status = '303 See Other', headers = [('Location', url)])

class Mapper(object):
    def __init__(self):
        self.paths = {}
        self.resources = {}
        self.default_path=''

    def __call__(self, environ, start_response):
        request = Request(environ)
        try:
            response = self.find_resource(request).handle(request, self.url)
        except StopIteration:
            raise
        except CustomResponse as r:
            response = r.response()
        except Exception as e:
            import traceback;
            traceback.print_exc()
            response = Response(traceback.format_exc(), status='500 not ok')
        return response(environ, start_response)


    def find_resource(self, request):
        if request.path == '/':
            raise SeeOther(self.default_path)
        path=request.path[1:].split('/')
        resource_class = self.resources[path[0]]
        query = dict([(k,v[0]) for k,v in request.args.items()])
        resource = resource_class(**query)
        return resource

    def register(self, resource, path=None, default=False):
        if path is None: 
            path = resource.__name__
        self.resources[path] = resource
        self.paths[resource] = path
        if default:
            self.default_path=path
        return resource

    def add(self):
        return self.register

    def default(self):
        return lambda resource: self.register(resource, default=True)

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
