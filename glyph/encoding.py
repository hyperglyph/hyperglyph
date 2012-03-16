from urlparse import urljoin
from StringIO import StringIO
from datetime import datetime

from pytz import utc

CONTENT_TYPE='application/vnd.glyph'

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


identity = lambda x:x
def _read_num(fh, term, parse):
    c = fh.read(1)
    buf=StringIO()
    while c != term:
        buf.write(c)
        c = fh.read(1)
    d = parse(buf.getvalue())
    return d, c
def read_first(fh):
    c = fh.read(1)
    while c in ('\n',' ','\t'):
        c = fh.read(1)
    return c
        


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

class Encoder(object):
    def __init__(self, node, extension):
        self.node = node
        self.extension = extension

    def dump(self, obj, resolver=identity):
        buf = StringIO()
        self._dump(obj, buf, resolver)
        return buf.getvalue()

    def parse(self, s, resolver=identity):
        buf = StringIO(s)
        return self.read(buf, resolver)


    def _dump(self, obj, buf, resolver):
        if obj is True:
            buf.write(TRUE)
        elif obj is False:
            buf.write(FALSE)
        elif obj is None:
            buf.write(NONE)
        elif isinstance(obj, (self.extension,)):
            buf.write(EXT)
            name, attributes, content = obj.__getstate__()
            obj.resolve(resolver)
            self._dump(name, buf, resolver)
            self._dump(attributes, buf, resolver)
            self._dump(content, buf, resolver)
        elif isinstance(obj, (self.node,)):
            buf.write(NODE)
            name, attributes, content = obj.__getstate__()
            self._dump(name, buf, resolver)
            self._dump(attributes, buf, resolver)
            self._dump(content, buf, resolver)
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
                self._dump(k, buf, resolver)
                self._dump(v, buf, resolver)
            buf.write(END)
        elif hasattr(obj, '__iter__'):
            buf.write(LIST)
            for x in obj:
                self._dump(x, buf, resolver)
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


    def _read_one(self, fh, c, resolver):
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
            flt_len = _read_num(fh, BLOB_SEP, parse=int)[0]
            buf= fh.read(flt_len)
            return float.fromhex(buf)

        elif c == LIST:
            first = read_first(fh)
            out = []
            while first != END:
                out.append(self._read_one(fh, first, resolver))
                first = read_first(fh)
            return out

        elif c == DICT:
            first = read_first(fh)
            out = {}
            while first != END:
                f = self._read_one(fh, first, resolver)
                second = read_first(fh)
                g = self._read_one(fh, second, resolver)
                new = out.setdefault(f,g)
                if new is not g:
                    raise StandardError('duplicate key')
                first = read_first(fh)
            return out
        elif c == NODE:
            first = read_first(fh)
            name = self._read_one(fh, first, resolver)
            first = read_first(fh)
            attr  = self._read_one(fh, first, resolver)
            first = read_first(fh)
            content = self._read_one(fh, first, resolver)
            return self.node.__make__(name, attr, content)
        elif c == EXT:
            first = read_first(fh)
            name = self._read_one(fh, first, resolver)
            first = read_first(fh)
            attr  = self._read_one(fh, first, resolver)
            first = read_first(fh)
            content = self._read_one(fh, first, resolver)
            ext= self.extension.__make__(name, attr, content)
            ext.resolve(resolver)
            return ext
        elif c == DTM:
            datestring = fh.read(26)
            dtm = datetime.strptime(datestring, "%Y-%m-%dT%H:%M:%S.%f").replace(tzinfo=utc)
            return dtm
        elif c not in ('', ):
            raise StandardError('decoding err', c)
        raise EOFError()


    def read(self, fh, resolver=identity):
        fh = wrapped(fh)
        try:
            first = read_first(fh)
            if first == '':
                raise EOFError()

            return self._read_one(fh, first, resolver)
        except EOFError as r:
            raise r
        except StandardError as e:
            raise 
            import traceback; traceback.print_exc() 
            raise StandardError('decoding %s'%(fh.getvalue()))

