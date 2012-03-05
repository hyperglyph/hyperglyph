from urlparse import urljoin
from StringIO import StringIO
import requests

from datetime import datetime
from pytz import utc


CONTENT_TYPE='application/glyph'

"""
glyph is a serialization format roughly based around bencoding

    json like vocabulary
        unicode -> u<len>:<utf-8 string>
        dict -> d<key><value><key><value>....e
        list -> l<item><item><item><item>....e
        float -> f<len>:<float in hex>
    additonal datatypes:
        num -> i<number>e
        byte str -> s<len>:<string>
        true -> T
        false -> F
        none -> N
        datetime -> D%Y-%m-%dT%H:%M:%S.%f


    xml like vocabulary
        node -> N<name item><attr item><children item>
            an object with a name, attributes and children
                attributes is nominally a dict.
                children nominally list
            think html5 microdata like
        ext -> X<item><item><item>
            like a node, but contains url, method, possibly form values.

    todo: timezones, periods?

    >>> dump([ 1, "2", {3:4}] )
    'li1es1:2di3ei4eee'
    >>> parse('li1es1:2di3ei4eee')
    [1, '2', {3: 4}]
    >>> parse('li1es1:2di3ei4eee')
    [1, '2', {3: 4}]
    >>> parse('lD2001-02-03T04:05:06.070000e')
    [datetime.datetime(2001, 2, 3, 4, 5, 6, 70000, tzinfo=<UTC>)]

"""
def node(name, attributes, children=None):
    return Node(name, attributes, children)

def form(url, method='POST',values=None):
    if values is None:
        if ismethod(url):
            values = methodargs(url)
        elif isinstance(url, type):
            values = methodargs(url.__init__)

    return Extension.make('form', {'method':method, 'url':url}, values)

def link(url, method='GET'):
    return Extension.make('link', {'method':method, 'url':url}, [])

def embed(url, content, method='GET'):
    return Extension.make('embed', {'method':method, 'url':url}, content)

def prop(url):
    return Extension.make('property', {'url':url}, [])

def ismethod(m, cls=None):
    return callable(m) and hasattr(m,'im_self') and (cls is None or isinstance(m.im_self, cls))

def methodargs(m):
    if ismethod(m):
        return m.func_code.co_varnames[1:]


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



HEADERS={'Accept': CONTENT_TYPE, 'Content-Type': CONTENT_TYPE}

session = requests.session()

def get(url, args=None,headers=None):
    return  fetch('GET', url, args, '', headers)

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

            
        for n,v in zip(names, args):
            data[n] = v

        for k,v in kwargs.items():
            if k in names:
                data[k]=v   

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

