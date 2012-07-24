from urlparse import urljoin
from datetime import datetime, timedelta
import collections
import io
import os
import itertools
import operator
import isodate
import tempfile

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
ODICT='O'
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
        if not isinstance(content, io.IOBase):
            if isinstance(content, unicode):
                content = io.StringIO(content)
            else:
                content = io.BytesIO(content)
        self.fh = content

    @property
    def content_type(self):
        return self._attributes[u'content-type']
    
    def __getattr__(self, attr):
        return getattr(self.__dict__["fh"], attr)


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


class Encoder(object):
    def __init__(self, node, extension, **kwargs):
        self.node = node
        self.extension = extension
        self.max_blob_mem_size = kwargs.get("max_blob_mem_size", 1024*1024*2)

    def dump(self, obj, resolver=identity, inline=fail):
        return self.dump_buf(obj, resolver, inline).read()

    def dump_buf(self, obj, resolver=identity, inline=fail):
        buf = io.BytesIO()
        for chunk in self._dump(obj, resolver, inline):
            buf.write(chunk)
        buf.seek(0)
        return buf
    
    def dump_iter(self, obj, chunk_size=-1, resolver=identity, inline=fail):
        buf = io.BytesIO()
        for chunk in self._dump(obj, resolver, inline):
            buf.write(chunk)

            if chunk_size > 0 and buf.tell() > chunk_size:
                buf.seek(0)
                new_chunk_size = yield buf.read(chunk_size)
                if new_chunk_size:
                    chunk_size = new_chunk_size
                tail = buf.read()
                buf.seek(0)
                buf.truncate(0)
                buf.write(tail)
             
        if buf.tell():
            yield buf.getvalue()
        

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
        elif hasattr(obj, 'iteritems'):
            if isinstance(obj, collections.OrderedDict):
                yield ODICT
            else:
                yield DICT
            for k in sorted(obj.keys()): # always sorted, so can compare serialized
                v=obj[k]
                for r in self._dump_one(k, resolver, inline, blobs): yield r
                for r in self._dump_one(v, resolver, inline, blobs): yield r
            yield END_DICT
        elif isinstance(obj, Blob):
            blob_id = len(blobs)
            blobs.append(obj.fh)
            yield BLOB
            yield str(blob_id)
            yield LEN_SEP
            for r in self._dump_one(obj._attributes, resolver, inline, blobs):
                yield r
            yield END_ITEM
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

        else:
            for r in self._dump_one(inline(obj), resolver, inline, blobs): yield r

    def _dump_blobs(self, blobs):
        for idx, b in enumerate(blobs):
            while True:
                data = b.read(8192)
                if not data:
                    break
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

        elif c == DICT or c == ODICT:
            first = read_first(fh)
            if c == ODICT:
                out = collections.OrderedDict()
            else:
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
            blobs[blob_id] = blob
            return blob

        elif c not in ('', ):
            raise StandardError('decoding err', c)
        raise EOFError()

    def _read_blobs(self, fh, blobs):
        byte_count = collections.defaultdict(int)
        while blobs:
            first = read_first(fh)
            if first == CHUNK:
                blob_id, first = _read_until(fh, (LEN_SEP,END_ITEM), parse=int)
                if first == END_ITEM: # 0 length block
                    blobs.pop(blob_id).seek(0)
                else:
                    size, first = _read_until(fh, LEN_SEP, parse=int)
                    blob = blobs[blob_id]
                    byte_count[blob_id] += blob.write(fh.read(size))
                    should_transfer = [
                        self.max_blob_mem_size is None,
                        byte_count[blob_id] >= self.max_blob_mem_size,
                    ]
                    if not isinstance(blob.fh, TemporaryFile) and any(should_transfer):
                        blob.seek(0)
                        finished = False
                        try:
                            tmp = TemporaryFile(suffix=str(blob_id))
                            tmp.write(blob.read())
                            finished = True
                        finally:
                            if not finished:
                                tmp.close()
                        blob.truncate(0)
                        blob.fh = tmp
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


class TemporaryFile(object):
    
    def __init__(self, *args, **kwargs):
        self.fd, self.name = tempfile.mkstemp(*args, **kwargs)
        self.file = io.open(self.fd, "w+b")
    
    def __repr__(self):
        return "<%s.%s object at %s>" % (self.__class__.__module__, self.__class__.__name__, self.name)
    
    def __getattr__(self, attr):
        return getattr(self.__dict__["file"], attr)
    
    def close(self):
        self.file.close()
        os.unlink(self.name)
