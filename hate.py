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
from urlparse import urljoin
from StringIO import StringIO
from datetime import datetime
from pytz import utc

import requests

from werkzeug.wrappers import Request, Response
from werkzeug.serving import make_server, WSGIRequestHandler

__all__ = [
    'CONTENT_TYPE','Server',
    'get', 'Mapper','map','Resource','r',
    'GET','PUT', 'POST', 'DELETE',
    'parse','dump','node','form','link',
]

CONTENT_TYPE='application/vnd.hate.hencode'

def get(url, args=None,headers=None):
    return  fetch('GET', url, args, '', headers)

def node(name, attributes, children=None):
    return Node(name, attributes, children)

def form(url, method='POST',values=()):
    return Extension.make('form', {'method':method, 'url':url}, values)

def link(url, method='GET'):
    return Extension.make('link', {'method':method, 'url':url}, [])

identity = lambda x:x

def dump(obj, resolver=identity):
    buf = StringIO()
    _dump(obj, buf, resolver)
    return buf.getvalue()

def parse(s, resolver=identity):
    #try:
        buf = StringIO(s)
        return read(buf, resolver)
    #except:
    #    raise StandardError('cantparse',s)


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








HEADERS={'Accept': CONTENT_TYPE, 'Content-Type': CONTENT_TYPE}

session = requests.session()

def fetch(method, url, args=None,data="", headers=None):
    if headers is None:
        headers = {}
    headers.update(HEADERS)
    if args is None:
        args = {}
    result = session.request(method, url, params=args, data=dump(data), headers=headers, allow_redirects=False)
    def join(u):
        return urljoin(result.url, u)
    if result.status_code in [ requests.codes.see_other]:
        return get(join(result.headers['Location']))
    elif result.status_code in [ requests.codes.created]:
        # never called
        return link(join(result.headers['Location']))
    data = result.content
    if result.headers['Content-Type'].startswith(CONTENT_TYPE):
        data = parse(data, join)
    return data




""" Data Types """

class Node(object):
    def __init__(self, name, attributes, content):
        self._name = name
        self._attributes = attributes
        self._content = content
    def __getstate__(self):
        return self._name, self._attributes, self._content

    def __setstate__(self, state):
        self._name = state[0]
        self._attributes = state[1]
        self._content = state[2]

    def __getattr__(self, name):
        try:
            return self._attributes[name]
        except KeyError:
            raise AttributeError(name)

    def __getitem__(self, name):
        return self._content[name]

    def __eq__(self, other):
        return self._name == other._name and self._attributes == other._attributes and self._content == other._content

    def __repr__(self):
        return '<node:%s %s %s>'%(self._name, repr(self._attributes), repr(self._content))

class Extension(Node):
    _exts = {}
    @classmethod
    def make(cls, name, attributes, content):
        ext = cls._exts.get(name, Node)
        return ext(name,attributes, content)
    
    @classmethod
    def register(cls, name):
        def _decorator(fn):
            cls._exts[name] = fn
            return fn
        return _decorator

    def __eq__(self, other):
        return isinstance(other, Extension) and Node.__eq__(self, other)

    def __repr__(self):
        return '<ext:%s %s %s>'%(self._name, repr(self._attributes), repr(self._content))

    def resolve(self, resolver):
        pass

@Extension.register('form')
class Form(Extension):
    def __call__(self, *args, **kwargs):
        url = self._attributes['url']
        data = {}
        names = self._content[:]

            
        for n,v in zip(args, names):
            data[n] = v

        for k,v in kwargs.items():
            if k in names:
                data[k]=v   

        return fetch(self._attributes.get('method','GET'),url, data=data)

    def resolve(self, resolver):
        print self._attributes['url'],
        self._attributes['url'] = resolver(self._attributes['url'])
        print self._attributes['url']

@Extension.register('link')
class Link(Extension):
    def __call__(self, *args, **kwargs):
        url = self._attributes['url']
        return fetch(self._attributes.get('method','GET'),url)

    def url(self):
        return self._attributes['url']
        
    def resolve(self, resolver):
        self._attributes['url'] = resolver(self._attributes['url'])

"""a serialization format roughly based around bencoding

    byte str -> s<len>:<string>
    unicode -> u<len>:<utf-8 string>
    dict -> d<key><value><key><value>....e
    list -> d<item><item><item><item>....e
    num -> i<number>e

    >>> dump([ 1, "2", {3:4}] )
    'li1es1:2di3ei4eee'
    >>> parse('li1es1:2di3ei4eee')
    [1, '2', {3: 4}]
    >>> parse('li1es1:2di3ei4eee')
    [1, '2', {3: 4}]
    >>> parse('lD2001-02-03T04:05:06.070000e')
    [datetime.datetime(2001, 2, 3, 4, 5, 6, 70000, tzinfo=<UTC>)]
"""

UNICODE_CHARSET="utf-8"

STR='s'
UNI='u'
BLOB_SEP=':'

FLT='f'
NUM='i'
DICT='d'
LIST='l'
DTM='D'
END='e'

TRUE='T'
FALSE='F'
NONE='N'

NODE='x'
EXT='X'


def _dump(obj, buf, resolver):
    if obj is True:
        buf.write(TRUE)
    elif obj is False:
        buf.write(FALSE)
    elif obj is None:
        buf.write(NONE)
    elif isinstance(obj, (Extension,)):
        buf.write(EXT)
        obj.resolve(resolver)
        _dump(obj._name, buf, resolver)
        _dump(obj._attributes, buf, resolver)
        _dump(obj._content, buf, resolver)
    elif isinstance(obj, (Node,)):
        buf.write(NODE)
        _dump(obj._name, buf, resolver)
        _dump(obj._attributes, buf, resolver)
        _dump(obj._content, buf, resolver)


    elif isinstance(obj, (str, buffer)):
        buf.write(STR)
        buf.write("%d"%len(obj))
        buf.write(BLOB_SEP)
        buf.write(obj)
    elif isinstance(obj, unicode):
        buf.write(UNI)
        obj = obj.encode(UNICODE_CHARSET)
        buf.write("%d"%len(obj))
        buf.write(BLOB_SEP)
        buf.write(obj)
    elif hasattr(obj, 'iteritems'):
        buf.write(DICT)
        for k in sorted(obj.keys()): # always sorted, so can compare serialized
            v=obj[k]
            _dump(k, buf, resolver)
            _dump(v, buf, resolver)
        buf.write(END)
    elif hasattr(obj, '__iter__'):
        buf.write(LIST)
        for x in obj:
            _dump(x, buf, resolver)
        buf.write(END)
    elif isinstance(obj, (int, long)):
        buf.write(NUM)
        buf.write(str(obj))
        buf.write(END)
    elif isinstance(obj, float):
        buf.write(FLT)
        obj= float.hex(obj)
        buf.write("%d"%len(obj))
        buf.write(BLOB_SEP)
        buf.write(obj)
    elif isinstance(obj, datetime):
        buf.write(DTM)
        obj = obj.astimezone(utc)
        buf.write(obj.strftime("%Y-%m-%dT%H:%M:%S.%f"))
    else:
        raise StandardError('cant encode', obj)


def _read_num(fh, term, parse):
    c = fh.read(1)
    buf=StringIO()
    while c != term:
        buf.write(c)
        c = fh.read(1)
    d = parse(buf.getvalue())
    return d, c

    

def _read_one(fh,c, resolver):
    if c == NONE:
        return None
    elif c == TRUE:
        return True
    elif c == FALSE:
        return False
    if c == STR or c == UNI:
        l = _read_num(fh, BLOB_SEP, parse=int)[0]
        buf= fh.read(l)
        if c == UNI:
            buf=buf.decode(UNICODE_CHARSET)
        return buf

    elif c == NUM:
        return _read_num(fh, END, parse=int)[0]

    elif c == FLT:
        l = _read_num(fh, BLOB_SEP, parse=int)[0]
        buf= fh.read(l)
        return float.fromhex(buf)

    elif c == LIST:
        first = fh.read(1)
        out = []
        while first != END:
            out.append(_read_one(fh, first, resolver))
            first = fh.read(1)
        return out

    elif c == DICT:
        first = fh.read(1)
        out = {}
        while first != END:
            f = _read_one(fh, first, resolver)
            second = fh.read(1)
            g = _read_one(fh, second, resolver)
            out[f]=g
            first = fh.read(1)
        return out
    elif c == NODE:
        first = fh.read(1)
        name = _read_one(fh, first, resolver)
        first = fh.read(1)
        attr  = _read_one(fh, first, resolver)
        first = fh.read(1)
        content = _read_one(fh, first, resolver)
        return Node(name, attr, content)
    elif c == EXT:
        first = fh.read(1)
        name = _read_one(fh, first, resolver)
        first = fh.read(1)
        attr  = _read_one(fh, first, resolver)
        first = fh.read(1)
        content = _read_one(fh, first, resolver)
        ext= Extension.make(name, attr, content)
        ext.resolve(resolver)
        return ext
    elif c == DTM:
        datestring = fh.read(26)
        dtm = datetime.strptime(datestring, "%Y-%m-%dT%H:%M:%S.%f").replace(tzinfo=utc)
        return dtm
    elif c not in ('', ):
        raise StandardError('decoding err', c)
    raise EOFError()

class wrapped(object):
    def __init__(self, fh):
        self.fh=fh
        self.buf=StringIO()

    def read(self,n):
        r= self.fh.read(n)
        self.buf.write(r)
        return r

    def getvalue(self):
        r= self.fh.read()
        self.buf.write(r)
        return self.buf.getvalue()


def read(fh, resolver=identity):
    fh = wrapped(fh)
    try:
        first = fh.read(1)
        while first =='\n':
            first = fh.read(1)
        if first == '':
            raise EOFError()

        return _read_one(fh, first, resolver)
    except EOFError as r:
        raise r
    except StandardError as e:
        raise 
        import traceback; traceback.print_exc() 
        raise StandardError('decoding %s'%(fh.getvalue()))




r = Resource
map = Mapper
