""" hate-rpc - websites for robots """
"""
Copyright (c) 2011-2012 Hanzo Archives Ltd

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included 
in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER 
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION 
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import collections
import cgi
import re
import threading
import socket

from urllib import urlencode
from datetime import datetime
from pytz import utc

from werkzeug.wrappers import Request, Response
from werkzeug.serving import make_server, WSGIRequestHandler

from hyperglyph import CONTENT_TYPE, dump, parse, get, Node, Extension

__all__ = [
    'CONTENT_TYPE','Server',
    'get', 'Mapper','map','Resource','r',
    'GET','PUT', 'POST', 'DELETE',
    'parse','dump','node','form','link',
]



def node(name, attributes, children=None):
    return Node(name, attributes, children)

def form(url, method='POST',values=()):
    return Extension.make('form', {'method':method, 'url':url}, values)

def link(url, method='GET'):
    return Extension.make('link', {'method':method, 'url':url}, [])



class Redirect(BaseException):
    def __init__(self, url):
        self.url = url

class Resource(object):
    def handle(self,request, resolver):
        method = request.method
        print request.path
        path = request.path[1:].split('/')[1:]
        data = request.data
        headers = request.headers

        if data:
            data = parse(data)
        else:
            data={}

        if path:
            path = path[0]

        print 'using path', path

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
        
        result = dump(result, resolver)
        return Response(result, content_type=CONTENT_TYPE)

    def get(self):
        doc = {}
        for k,v in self.__dict__.items():
            doc[k] = v
        
        for m in self.__class__.__dict__:
            if not m.startswith('__'):
                attr = getattr(self,m)
                if hasattr(attr, 'func_code'):
                    doc[m] = form(attr, values=attr.func_code.co_varnames[1:])
        return node(self.__class__.__name__, attributes=doc)


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
        except CustomResponse as r:
            response = r.response()
        except BaseException as e:
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


class RequestHandler(WSGIRequestHandler):
    def log_request(self, code='-', size='-'):
        pass

class Server(threading.Thread):
    def __init__(self, app, host="", port=0, threaded=True, processes=1,
                request_handler=RequestHandler, passthrough_errors=False, ssl_context=None):
        """ Use ssl_context='adhoc' for an ad-hoc cert, a tuple for a (cerk, pkey) files
            
        
        """
        threading.Thread.__init__(self)
        self.daemon=True
        self.server = make_server(host, port, app, threaded=threaded, processes=processes,
            request_handler=request_handler, passthrough_errors=passthrough_errors, ssl_context=ssl_context)

    @property
    def url(self):
        return 'http%s://%s:%d/'%(('s' if self.server.ssl_context else ''), self.server.server_name, self.server.server_port)

    def run(self):
        self.server.serve_forever()

    def stop(self):
        self.server.shutdown_signal = True
        if self.server and self.is_alive():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect((self.server.server_name, self.server.server_port))
                s.send('\r\n')
                s.close()
            except IOError:
                import traceback
                traceback.print_exc()
        self.join(5)










r = Resource
map = Mapper
