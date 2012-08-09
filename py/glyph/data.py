from urlparse import urljoin
import datetime
import io
import requests
import collections
from urlparse import urljoin

from pytz import utc

from .encoding import Encoder, CONTENT_TYPE, Blob

HEADERS={'Accept': CONTENT_TYPE, 'Content-Type': CONTENT_TYPE}
CHUNKED = False # wsgiref is terrible - enable by default when the default wsgi server works
session = requests.session()

def utcnow():
    return datetime.datetime.utcnow().replace(tzinfo=utc)


def robj(obj, contents):
    return Extension.__make__(u'resource', {u'name':unicode(obj.__class__.__name__), u'url': obj}, contents)

def form(url, method=u'POST',values=None):
    if values is None:
        if ismethod(url):
            values = methodargs(url)
        elif isinstance(url, type):
            values = methodargs(url.__init__)
        elif callable(url):
            values = funcargs(url)

    if values is not None:
        values = [form_input(v) for v in values]

    return Extension.__make__(u'form', {u'method':method, u'url':url, u'values':values}, None)

def link(url, method='GET'):
    return Extension.__make__(u'link', {u'method':method, u'url':url}, None)

def embedlink(url, content, method=u'GET'):
    return Extension.__make__(u'link', {u'method':method, u'url':url, u'inline':True}, content)

def error(reference, message):
    return Extension.__make__(u'error', {u'logref':unicode(reference), u'message':message}, {})

def form_input(name):
    #return unicode(name)
    return Extension.__make__(u'input', {u'name':unicode(name)}, None)


# move to inspect ?

def ismethod(m, cls=None):
    return callable(m) and hasattr(m,'im_self') and (cls is None or isinstance(m.im_self, cls))

def methodargs(m):
    if ismethod(m):
        return m.func_code.co_varnames[1:m.func_code.co_argcount]

def funcargs(m):
    return m.func_code.co_varnames[:m.func_code.co_argcount]

def get(url, args=None, headers=None):
    if hasattr(url, u'url'):
        url = url.url()
    return fetch('GET', url, args, None, headers)


# wow, transfer-chunked encoding is ugly.

class chunk_fh(object):
    def __init__(self, data):
        self.g = data
        self.state = 0
        self.buf = io.BytesIO()

    def read(self,size=-1):
        """ we need to conform to the defintion of read,
            don't return pieces bigger than size, and return all when size =< 0
        """
        if size > 0:
            while self.buf.tell() < size:
                if not self.read_chunk(size):
                    break
        else:
            while self.read_chunk(size):
                pass

        self.buf.seek(0)
        ret = self.buf.read(size)
        tail = self.buf.read()
        self.buf.seek(0)
        self.buf.truncate(0)
        self.buf.write(tail)

        return ret
        
    def read_chunk(self, size):
        chunk_size = max(1, size-4-len("%s"%size)) if size > 0 else size

        try:
            if self.state > 0:
                chunk = self.g.send(chunk_size)
            elif self.state == 0:
                self.g = dump_iter(self.g, chunk_size=chunk_size)
                chunk = self.g.next()
                self.state = 1
            elif self.state < 0:
                return False
                
            self.buf.write("%X\r\n%s\r\n"%(len(chunk), chunk))
        except (GeneratorExit, StopIteration):
            self.state = -1
            self.buf.write("0\r\n\r\n")

        return self.state > 0
                
def fetch(method, url, args=None, data=None, headers=None, force_method=None):
    if headers is None:
        headers = {}
    headers.update(HEADERS)

    if force_method and method != force_method:
        headers['Method'] = method
        method = force_method

    if args is None:
        args = {}
    if data is not None:
        if CHUNKED:
            headers["Transfer-Encoding"] = "chunked"
            data = chunk_fh(data)
        else:
            data = dump(data)
    result = session.request(method, url, params=args, data=data, headers=headers, allow_redirects=False)
    def join(u):
        return urljoin(result.url, u)
    if result.status_code == 303: # See Other
        return get(join(result.headers['Location']))
    elif result.status_code == 204: # No Content
        return None
    elif result.status_code == 201: # 
        # never called
        return link(join(result.headers['Location']))

    result.raise_for_status()
    data = result.content
    if result.headers['Content-Type'].startswith(CONTENT_TYPE):
        data = parse(data, base_url=result.url)
    return data


class BaseNode(object):
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

    def __eq__(self, other):
        return self._name == other._name and self._attributes == other._attributes and self._content == other._content

    @classmethod
    def __make__(cls, name, attributes, content):
        return cls(name,attributes, content)

    def __resolve__(self, resolver):
        pass

    @staticmethod
    def __rebase__(name, attr, base_url):
        return attr, base_url

class Extension(BaseNode):
    _exts = {}
    @classmethod
    def __make__(cls, name, attributes, content):
        ext = cls._exts[name]
        return ext(name,attributes, content)
    
    @classmethod
    def register(cls, name):
        def _decorator(fn):
            cls._exts[name] = fn
            return fn
        return _decorator

    def __eq__(self, other):
        return isinstance(other, Extension) and BaseNode.__eq__(self, other)

    def __repr__(self):
        return '<ext:%s %s %s>'%(self._name, repr(self._attributes), repr(self._content))

    @staticmethod
    def __rebase__(name, attr, base_url):
        if u'url' in attr: #and name in (u"form", u"link", u"resource", u"error"):
            attr[u'url'] = urljoin(base_url, attr[u'url'])
            return attr, attr[u'url']
        else:
            return attr, base_url

@Extension.register('form')
class Form(Extension):
    def __call__(self, *args, **kwargs):
        if self._attributes.get(u'headers'):
            raise NotImplementedError('TODO 0.5 headers in forms')

        if self._attributes.get(u'envelope', u'form') != u'form':
            raise NotImplementedError('TODO 0.8 envelope types in forms')

        url = self._attributes[u'url']

        parameters = collections.OrderedDict()

        # convert all inputs to a ord-dict of form inputs
        if self._attributes[u'values']:
            for n in self._attributes[u'values']:
                if isinstance(n, Input):
                    parameters[n.name] = n
                else:
                    parameters[n] = form_input(n)


        # build the form arguments
        data = collections.OrderedDict()

        if parameters:
            args = list(args)
            kwargs = dict(kwargs)

            for p,i in parameters.iteritems():
                if args:
                    data[p] = i.convert(args.pop(0))
                elif p in kwargs:
                    data[p] = i.convert(kwargs.pop(p))
                elif i.has_default():
                    data[p] = i.default()
                else:
                    raise TypeError('argument %s missing'%p)
            if args:
                raise TypeError('function passed %d extra parameter(s)'%len(args))
            elif kwargs:
                raise TypeError('function passed %d extra named parameter(s)'%len(kwargs))
                
        elif args or kwargs:
            raise TypeError('function takes 0 arguments')

        headers = {}

        #data = [(k,v) for k,v in data.iteritems()]

        return fetch(self._attributes.get(u'method',u'POST'), url, data=data, force_method=u'POST')

    def __resolve__(self, resolver):
        self._attributes[u'url'] = unicode(resolver(self._attributes[u'url']))

@Extension.register('link')
class Link(Extension):
    def __call__(self, *args, **kwargs):
        if self._attributes.get(u'headers'):
            raise NotImplementedError('TODO 0.5 headers in forms')

        if self._attributes.get(u'inline', False):
            return self._content
        else:
            url = self._attributes[u'url']
            return fetch(self._attributes.get(u'method',u'GET'),url, force_method=u'GET')

    def url(self):
        return self._attributes[u'url']
        
    def __resolve__(self, resolver):
        self._attributes[u'url'] = unicode(resolver(self._attributes[u'url']))



@Extension.register('resource')
class Resource(Extension):
        
    def __resolve__(self, resolver):
        self._attributes[u'url'] = unicode(resolver(self._attributes[u'url']))

    def __getattr__(self, name):
        try:
            return self._content[name]
        except KeyError:
            raise AttributeError(name)


@Extension.register('error')
class Error(Extension):
    @property
    def message(self):
        return self._attributes[u'message']

    @property
    def logref(self):
        return self._attributes[u'logref']


@Extension.register('input')
class Input(Extension):
    @property
    def name(self):
        return self._attributes[u'name']

    def convert(self, value):
        return value

    def has_default(self):
        return u'value' in self._attributes

    def default(self):
        return self._attributes[u'value']

@Extension.register('collection')
class Collection(Extension):
    pass
_encoder = Encoder(extension=Extension)

dump = _encoder.dump
dump_iter = _encoder.dump_iter
dump_buf = _encoder.dump_buf
parse = _encoder.parse
read = _encoder.read
