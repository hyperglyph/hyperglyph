from urlparse import urljoin
from datetime import datetime, timedelta
import io
import itertools
import operator
import isodate

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

def blob(content, content_type=u"application/octet-stream"):
    return Blob(content, {u'content-type':content_type,})

class Blob(object):
    def __init__(self, content, attributes):
        self._attributes = attributes

        if isinstance(content, list):
            content = "".join(content)
        if not isinstance(content, io.IOBase):
            if isinstance(content, unicode):
                content = io.StringIO(content)
            else:
                content = io.BytesIO(content)
        self.fh = content

    @property
    def content_type(self):
        return self._attributes[u'content-type']


identity = lambda x:x

def fail():
    raise StandardError()

def _read_until(fh, term, parse=identity, skip=None):
    c = fh.read(1)
    buf = io.BytesIO()
    while c not in term and c != skip:
        buf.write(c)
        c = fh.read(1)
    if c in term:
        d = parse(buf.getvalue())
        return d, c
    else:
        return None, c

def read_first(fh):
    c = fh.read(1)
    while c in ('\r','\v','\n',' ','\t'):
        c = fh.read(1)
    return c



def chunker(iterable, n):
    """
    Given an iterable yield chunks of size N
    """
    args = [iter(iterable)] * n
    for bits in itertools.izip_longest(itertools.chain.from_iterable(args), fillvalue=""):
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
        iterator = self._dump(obj, resolver, inline)
        chunks = iterator if chunk_size is None else chunker(iterator, chunk_size)
        for chunk in chunks:
            yield chunk

    def parse(self, stream, resolver=identity):
        if not hasattr(stream, "read"):
            stream = io.BytesIO(stream)
        return self.read(stream, resolver)

    def _dump(self, obj, resolver, inline):
        blobs = []
        for o in self._dump_one(obj, resolver, inline, blobs):
            yield o
        for o in self._dump_blobs(blobs):
            yield o

    def _dump_one(self, obj, resolver, inline, blobs):
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
            for r in self._dump_one(name, resolver, inline, blobs): 
                yield r
            for r in self._dump_one(attributes, resolver, inline, blobs):
                yield r
            for r in self._dump_one(content, resolver, inline, blobs):
                yield r
            yield END_EXT
        
        elif isinstance(obj, (self.node,)):
            yield NODE
            name, attributes, content = obj.__getstate__()
            for r in self._dump_one(name, resolver, inline, blobs): yield r
            for r in self._dump_one(attributes, resolver, inline, blobs): yield r
            for r in self._dump_one(content, resolver, inline, blobs): yield r
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
                for r in self._dump_one(x, resolver, inline, blobs): yield r
            yield END_SET
        elif isinstance(obj, io.IOBase):
            yield LIST
            while True:
                data = obj.read(4096)
                if not data:
                    break
                for r in self._dump_one(data, resolver, inline, blobs): yield r
            yield END_LIST
        elif hasattr(obj, 'iteritems'):
            yield DICT
            for k in sorted(obj.keys()): # always sorted, so can compare serialized
                v=obj[k]
                for r in self._dump_one(k, resolver, inline, blobs): yield r
                for r in self._dump_one(v, resolver, inline, blobs): yield r
            yield END_DICT

        elif hasattr(obj, '__iter__'):
            yield LIST
            for x in obj:
                for r in self._dump_one(x, resolver, inline, blobs): yield r
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
            yield PER
            yield isodate.duration_isoformat(obj)
            yield END_ITEM
        elif isinstance(obj, Blob):
            blob_id = len(blobs)
            blobs.append(obj.fh)
            yield BLOB
            yield str(blob_id)
            yield LEN_SEP
            for r in self._dump_one(obj._attributes, resolver, inline, blobs):
                yield r
            yield END_ITEM

        else:
            try:
                for r in self._dump_one(inline(obj), resolver, inline, blobs): yield r
            except StandardError:
                raise StandardError('Failed to encode (%s)' % repr(obj))

    def _dump_blobs(self, blobs):
        for idx, b in enumerate(blobs):
            data = b.read()
            yield CHUNK
            yield str(idx)
            yield LEN_SEP
            yield str(len(data))
            yield LEN_SEP
            yield data
            yield END_ITEM

            yield CHUNK
            yield str(idx)
            yield END_ITEM


    def _read_one(self, fh, c, resolver, blobs):
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
                item = self._read_one(fh, first, resolver, blobs)
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
                out.append(self._read_one(fh, first, resolver, blobs))
                first = read_first(fh)
            return out

        elif c == DICT:
            first = read_first(fh)
            out = {}
            while first != END_DICT:
                f = self._read_one(fh, first, resolver, blobs)
                second = read_first(fh)
                g = self._read_one(fh, second, resolver, blobs)
                new = out.setdefault(f,g)
                if new is not g:
                    raise StandardError('duplicate key')
                first = read_first(fh)
            return out
        elif c == NODE:
            first = read_first(fh)
            name = self._read_one(fh, first, resolver, blobs)
            first = read_first(fh)
            attr  = self._read_one(fh, first, resolver, blobs)
            first = read_first(fh)
            content = self._read_one(fh, first, resolver, blobs)
            first = read_first(fh)
            if first != END_NODE:
                    raise StandardError('NODE')
            return self.node.__make__(name, attr, content)
        elif c == EXT:
            first = read_first(fh)
            name = self._read_one(fh, first, resolver, blobs)
            first = read_first(fh)
            attr  = self._read_one(fh, first, resolver, blobs)
            first = read_first(fh)
            content = self._read_one(fh, first, resolver, blobs)
            first = read_first(fh)
            if first != END_EXT:
                    raise StandardError('ext')
            ext= self.extension.__make__(name, attr, content)
            ext.__resolve__(resolver)
            return ext
        elif c == PER:
            period = _read_until(fh, END_ITEM)[0]
            return isodate.parse_duration(period)
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
        elif c == BLOB:
            blob_id, first = _read_until(fh, LEN_SEP, parse=int)
            first = read_first(fh)
            attr  = self._read_one(fh, first, resolver, blobs)
            blob = Blob(io.BytesIO(), attr)
            first = read_first(fh)
            if first != END_ITEM:
                    raise StandardError('blob')
            blobs[blob_id] = blob.fh
            return blob

        elif c not in ('', ):
            raise StandardError('decoding err', c)
        raise EOFError()

    def _read_blobs(self, fh, blobs):
        while blobs:
            first = read_first(fh)
            if first == CHUNK:
                blob_id, first = _read_until(fh, (LEN_SEP,END_ITEM), parse=int)
                if first == END_ITEM: # 0 length block
                    blobs.pop(blob_id).seek(0)
                else:
                    size, first = _read_until(fh, LEN_SEP, parse=int)
                    blobs[blob_id].write(fh.read(size))
                    first = read_first(fh)

                if first != END_ITEM:
                    raise StandardError('blob')
                    
            else:
                raise StandardError('chunk')

    def read(self, fh, resolver=identity):
        blobs = {}
        first = read_first(fh)
        if first == '':
            raise EOFError()
        result = self._read_one(fh, first, resolver, blobs)
        self._read_blobs(fh, blobs)
        return result

