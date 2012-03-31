from urlparse import urljoin
import datetime

from pytz import utc

from .encoding import Encoder, CONTENT_TYPE


def utcnow():
    datetime.datetime.utcnow().replace(tzinfo=utc)


def node(name, attributes, children=None):
    return Node(name, attributes, children)

def form(url, method='POST',values=None):
    if values is None:
        if ismethod(url):
            values = methodargs(url)
        elif isinstance(url, type):
            values = methodargs(url.__init__)
        elif callable(url):
            values = funcargs(url)

    return Extension.__make__('form', {'method':method, 'url':url}, values)

def link(url, method='GET'):
    return Extension.__make__('link', {'method':method, 'url':url}, [])

def embed(url, content, method='GET'):
    return Extension.__make__('embed', {'method':method, 'url':url}, content)

def prop(url):
    return Extension.__make__('property', {'url':url}, [])


# move to inspect ?

def ismethod(m, cls=None):
    return callable(m) and hasattr(m,'im_self') and (cls is None or isinstance(m.im_self, cls))

def methodargs(m):
    if ismethod(m):
        return m.func_code.co_varnames[1:]

def funcargs(m):
    return m.func_code.co_varnames[:]



def get(url, args=None,headers=None):
    if hasattr(url, 'url'):
        url = url.url()
    return  fetch('GET', url, args, None, headers)


HEADERS={'Accept': CONTENT_TYPE, 'Content-Type': CONTENT_TYPE}
try:
    import requests
    session = requests.session()
except:
    import urllib2, urllib, collections
    Result = collections. namedtuple('Result', 'url, status_code, content,  headers,  raise_for_status') 
    opener = urllib2.build_opener(urllib2.HTTPHandler)
    class session(object):
        @staticmethod

        def request(method, url, params, data, headers, allow_redirects):
            url = "%s?%s" % (url, urllib.urlencode(params)) if params else url

            if data:
                req = urllib2.Request(url, data)
            else:
                req = urllib2.Request(url)

            for header, value in headers.items():
                req.add_header(header, value)
            req.get_method = lambda: method
            try:
                result = opener.open(req)

                return Result(result.geturl(), result.code, result.read(), result.info(), lambda: None)
            except StopIteration: # In 2.7 this does not derive from Exception
                raise
            except StandardError as e:
                import traceback
                traceback.print_exc()
                raise StandardError(e)

def fetch(method, url, args=None,data=None, headers=None):
    if headers is None:
        headers = {}
    headers.update(HEADERS)
    if args is None:
        args = {}
    if data is not None:
        data=dump(data)
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
        data = parse(data, join)
    return data


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

    @classmethod
    def __make__(cls, name, attributes, content):
        return cls(name,attributes, content)

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
    def __make__(cls, name, attributes, content):
        ext = cls._exts.get(name, node)
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
        if self._content:
            names = self._content[:]

            for n,v in zip(names, args):
                data[n] = v
        elif args:
            raise StandardError('no unamed arguments')

        for k,v in kwargs.items():
            if k in names:
                data[k]=v   
            else:
                raise StandardError('unknown argument')

        return fetch(self._attributes.get('method','GET'),url, data=data)

    def resolve(self, resolver):
        self._attributes['url'] = resolver(self._attributes['url'])

@Extension.register('link')
class Link(Extension):
    def __call__(self, *args, **kwargs):
        url = self._attributes['url']
        return fetch(self._attributes.get('method','GET'),url)

    def url(self):
        return self._attributes['url']
        
    def resolve(self, resolver):
        self._attributes['url'] = resolver(self._attributes['url'])


@Extension.register('embed')
class Embed(Extension):
    def __call__(self, *args, **kwargs):
        return self._content

    def url(self):
        return self._attributes['url']
        
    def resolve(self, resolver):
        self._attributes['url'] = resolver(self._attributes['url'])

_encoder = Encoder(node=Node, extension=Extension)

dump = _encoder.dump
parse = _encoder.parse
read = _encoder.read
