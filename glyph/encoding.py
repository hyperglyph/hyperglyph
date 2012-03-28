from urlparse import urljoin
from StringIO import StringIO
from datetime import datetime

from pytz import utc

CONTENT_TYPE='application/vnd.glyph'

"""
glyph is a serialization format roughly based around bencoding


    strings!:
        unicode -> u <byte len> \x0a <utf-8 string>
        byte str -> s <byte len> \x0a  <byte string>

    numbers:
        datetime -> d %Y-%m-%dT%H:%M:%S.%f \x0a
        num -> i <number> \x0a
        float -> f <float in hex> \x0a

    collections:
        dict -> D <key> <value> <key> <value>....E
            no duplicates allowed, in asc sorted order by key
        list -> L <item> <item> <item> <item>....E
            
        set  -> S <item> <item> <item> <item>....E
            no duplicates, in asc sorted order

    additonal datatypes:
        true -> T
        false -> F
        none -> N


    xml like vocabulary
        node -> X<name item><attr item><children item>
            an object with a name, attributes and children
                attributes is nominally a dict.
                children nominally list
            think html5 microdata like
        ext -> Y<item><item><item>
            like a node, but contains url, method, possibly form values.

    todo: timezones, periods?


"""

UNICODE_CHARSET="utf-8"

STR='s'
UNI='u'
END_ITEM='\x0a'

FLT='f'
NUM='i'
DTM='d'

DICT='D'
LIST='L'
SET='S'
END_DICT = END_LIST = END_SET ='E'

TRUE='T'
FALSE='F'
NONE='N'

NODE='X'
EXT='Y'



identity = lambda x:x
def _read_until(fh, term, parse=identity):
    if term == '\n':
        line = fh.readline()
        d, c = parse(line[:-1]), line[-1]
    else:
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

    def readline(self):
        r= self.fh.readline()
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
            buf.write(END_ITEM)
            buf.write(obj)
        
        elif isinstance(obj, unicode):
            buf.write(UNI)
            obj = obj.encode(UNICODE_CHARSET)
            buf.write("%d"%len(obj))
            buf.write(END_ITEM)
            buf.write(obj)
        
        elif isinstance(obj, set):
            buf.write(SET)
            for x in sorted(obj):
                self._dump(x, buf, resolver)
            buf.write(END_SET)
        elif hasattr(obj, 'iteritems'):
            buf.write(DICT)
            for k in sorted(obj.keys()): # always sorted, so can compare serialized
                v=obj[k]
                self._dump(k, buf, resolver)
                self._dump(v, buf, resolver)
            buf.write(END_DICT)

        elif hasattr(obj, '__iter__'):
            buf.write(LIST)
            for x in obj:
                self._dump(x, buf, resolver)
            buf.write(END_LIST)
        elif isinstance(obj, (int, long)):
            buf.write(NUM)
            buf.write(str(obj))
            buf.write(END_ITEM)
        elif isinstance(obj, float):
            buf.write(FLT)
            obj= float.hex(obj)
            buf.write(obj)
            buf.write(END_ITEM)
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
            l = _read_until(fh, END_ITEM, parse=int)[0]
            buf= fh.read(l)
            if c == UNI:
                buf=buf.decode(UNICODE_CHARSET)
            return buf

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

