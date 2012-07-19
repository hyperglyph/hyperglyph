from urlparse import urljoin
from cStringIO import StringIO
from datetime import datetime, timedelta
import io
import itertools
import operator

from pytz import utc

CONTENT_TYPE='application/vnd.glyph'

UNICODE_CHARSET="utf-8"

BSTR='b'
UNI='u'
LEN_SEP=':'
END_ITEM=';'
END_NODE = END_EXT = END_DICT = END_LIST = END_SET = END_ITEM

FLT='f'
NUM='i'
DTM='d'
PER='p'

DICT='D'
LIST='L'
SET='S'

TRUE='T'
FALSE='F'
NONE='N'

NODE='X'
EXT='H'
BLOB = 'B'
CHUNK = 'c'



identity = lambda x:x

def fail():
    raise StandardError()

def _read_until(fh, term, parse=identity, skip=None):
    c = fh.read(1)
    buf=StringIO()
    while c != term and c != skip:
        buf.write(c)
        c = fh.read(1)
    if c == term:
        d = parse(buf.getvalue())
        return d, c
    else:
        return None, c

def read_first(fh):
    c = fh.read(1)
    while c in ('\r','\v','\n',' ','\t'):
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

    def readline(self):
        r= self.fh.readline()
        self.buf.write(r)
        return r

    def getvalue(self):
        r= self.fh.read()
        self.buf.write(r)
        return self.buf.getvalue()


def forever(iterable):
    """
    Given an iterable yield bytes from all the nested iterators.
    """
    for x in iterable:
        if isinstance(x, basestring):
            for c in x:
                yield c
        else:
            for y in forever(x):
                yield y


def chunker(iterable, n):
    """
    Given an iterable yield chunks of size N
    """
    args = [iter(iterable)] * n
    for bits in itertools.izip_longest(fillvalue="", *args):
        yield reduce(operator.add, bits)


class Encoder(object):
    def __init__(self, node, extension):
        self.node = node
        self.extension = extension

    def dump(self, *args, **kwargs):
        buf = io.BytesIO()
        kwargs.setdefault("chunk_size", 4096)
        for chunk in self.dump_iter(*args, **kwargs):
            buf.write(chunk)
        buf.seek(0)
        return buf.read()
    
    def dump_iter(self, obj, resolver=identity, inline=fail, chunk_size=None):
        iterator = forever(self._dump(obj, resolver, inline))
        chunks = iterator if chunk_size is None else chunker(iterator, chunk_size)
        for chunk in chunks:
            yield chunk

    def parse(self, s, resolver=identity):
        buf = StringIO(s)
        return self.read(buf, resolver)


    def _dump(self, obj, resolver, inline):
        if obj is True:
            yield TRUE
            yield END_ITEM

        elif obj is False:
            yield FALSE
            yield END_ITEM
        
        elif obj is None:
            yield NONE
            yield END_ITEM
        
        elif isinstance(obj, (self.extension,)):
            yield EXT
            name, attributes, content = obj.__getstate__()
            obj.__resolve__(resolver)
            yield self._dump(name, resolver, inline)
            yield self._dump(attributes, resolver, inline)
            yield self._dump(content, resolver, inline)
            yield END_EXT
        
        elif isinstance(obj, (self.node,)):
            yield NODE
            name, attributes, content = obj.__getstate__()
            yield self._dump(name, resolver, inline)
            yield self._dump(attributes, resolver, inline)
            yield self._dump(content, resolver, inline)
            yield END_NODE
        
        elif isinstance(obj, (str, buffer)):
            yield BSTR
            if len(obj) > 0:
                yield "%d" % len(obj)
                yield LEN_SEP
                yield obj
            yield END_ITEM
        
        elif isinstance(obj, unicode):
            yield UNI
            obj = obj.encode(UNICODE_CHARSET)
            if len(obj) > 0:
                yield "%d" % len(obj)
                yield LEN_SEP
                yield obj
            yield END_ITEM
        
        elif isinstance(obj, set):
            yield SET
            for x in sorted(obj):
                yield self._dump(x, resolver, inline)
            yield END_SET
        elif isinstance(obj, io.IOBase):
            yield LIST
            while True:
                data = obj.read(4096)
                if not data:
                    break
                yield self._dump(data, resolver, inline)
            yield END_LIST
        elif hasattr(obj, 'iteritems'):
            yield DICT
            for k in sorted(obj.keys()): # always sorted, so can compare serialized
                v=obj[k]
                yield self._dump(k, resolver, inline)
                yield self._dump(v, resolver, inline)
            yield END_DICT

        elif hasattr(obj, '__iter__'):
            yield LIST
            for x in obj:
                yield self._dump(x, resolver, inline)
            yield END_LIST
        elif isinstance(obj, (int, long)):
            yield NUM
            yield str(obj)
            yield END_ITEM
        elif isinstance(obj, float):
            yield FLT
            obj = float.hex(obj)
            yield obj
            yield END_ITEM
        elif isinstance(obj, datetime):
            yield DTM
            obj = obj.astimezone(utc)
            yield obj.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            yield END_ITEM
        elif isinstance(obj, timedelta):
            raise NotImplementedError()
            yield PER
            yield
            yield END_ITEM
        else:
            try:
                yield self._dump(inline(obj), resolver, inline)
            except StandardError:
                raise StandardError('Failed to encode (%s)' % repr(obj))


    def _read_one(self, fh, c, resolver):
        if c == NONE:
            _read_until(fh, END_ITEM)
            return None
        elif c == TRUE:
            _read_until(fh, END_ITEM)
            return True
        elif c == FALSE:
            _read_until(fh, END_ITEM)
            return False
        if c == BSTR or c == UNI:
            size, first = _read_until(fh, LEN_SEP, parse=int, skip=END_ITEM)
            if first == LEN_SEP:
                buf= fh.read(size)
                first = read_first(fh)
            else:
                buf = b''

            if c == UNI:
                buf=buf.decode(UNICODE_CHARSET)
            if first == END_ITEM:
                return buf
            else:
                raise StandardError('error')

        elif c == NUM:
            return _read_until(fh, END_ITEM, parse=int)[0]

        elif c == FLT:
            return _read_until(fh, END_ITEM, parse=float.fromhex)[0]

        elif c == SET:
            first = read_first(fh)
            out = set()
            while first != END_SET:
                item = self._read_one(fh, first, resolver)
                if item not in out:
                    out.add(item)
                else:
                    raise StandardError('duplicate key')
                first = read_first(fh)
            return out

        elif c == LIST:
            first = read_first(fh)
            out = []
            while first != END_LIST:
                out.append(self._read_one(fh, first, resolver))
                first = read_first(fh)
            return out

        elif c == DICT:
            first = read_first(fh)
            out = {}
            while first != END_DICT:
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
            first = read_first(fh)
            if first != END_NODE:
                    raise StandardError('NODE')
            return self.node.__make__(name, attr, content)
        elif c == EXT:
            first = read_first(fh)
            name = self._read_one(fh, first, resolver)
            first = read_first(fh)
            attr  = self._read_one(fh, first, resolver)
            first = read_first(fh)
            content = self._read_one(fh, first, resolver)
            first = read_first(fh)
            if first != END_EXT:
                    raise StandardError('ext')
            ext= self.extension.__make__(name, attr, content)
            ext.__resolve__(resolver)
            return ext
        elif c == PER:
            periodstring =  _read_until(fh, END_ITEM)[0]
            raise NotImplementedError()
        elif c == DTM:
            datestring =  _read_until(fh, END_ITEM)[0]
            if datestring[-1].lower() == 'z':
                if '.' in datestring:
                    datestring, sec = datestring[:-1].split('.')
                    date = datetime.strptime(datestring, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=utc)
                    sec = float("0."+sec)
                    return date + timedelta(seconds=sec)
                else:
                    return datetime.strptime(datestring, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=utc)

            raise StandardError('decoding date err', datestring)
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

