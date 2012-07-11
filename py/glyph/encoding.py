from urlparse import urljoin
from cStringIO import StringIO
from datetime import datetime, timedelta

from pytz import utc

CONTENT_TYPE='application/vnd.glyph'

"""
glyph is a serialization format roughly based around bencoding
with support for hypermedia types (links, forms).


    strings!:
        utf-8 string -> u <byte len> \x0a <utf-8 string>
        byte string -> b <byte len> \x0a  <byte string>

    numbers:
        utc datetime -> d %Y-%m-%dT%H:%M:%S.%fZ \x0a
            note: currently only UTC times supported,
                  so all datetimes must end with Z

        num -> i <number> \x0a
            arbitrary precision whole number

        float -> f <float in hex> \x0a
            float or double - the hex format is from
            c99 
            

    collections:
        list -> L <item> <item> <item> <item>....E
            
        dict -> D <key> <value> <key> <value>....E
            no duplicates allowed

        set  -> S <item> <item> <item> <item>....E
            no duplicates


    singleton datatypes:
        true -> T
        false -> F
        none -> N

    xml like three item tuples (name, attributes, children)
        node -> X<name item><attr item><children item>
            an object with a name, attributes and children
                attributes is nominally a dict.
                children nominally list
            think html5 microdata like

    hypermedia types/extensions: 
        ext -> H<item><item><item>
            like a node, but contains url, method, possibly form values.

    currently the following extensions are defined:
        link, form and embed.

        all dictionary keys *should* be utf-8

        link:   
            name is "link"
            attr is a dict, containing the following keys:
                url, method
                
            children is None

        form:   
            name is "form"
            attr is a dict, containing the following keys:
                url, method
                
            children is currently a list of names
            for the form to submit

            currently to submit a form, a dictionary is sent back

        embed
            name is "embed"
            attr is a dict, containing the following keys:
                url, method
                
            children is the object that would be returned
            from fetching that link

        

    notes:
        utf-8 vs bytestrings in dictionary keys/values
        is a hard one.

        i'm working on it
                

    whitespace/newlines
        parser can ignore whitespace when it is safe to do so
        parser can treat CRLF as LF


    unordered collections:
        for the unordered collections, it is recommended
        to order them in some way, such that the serializing
        is consistent within the library, i.e

            dump(dict) equals dump(parse(dump(dict)))

        but the ordering is ignored when reading.

    todo: timezones, periods?


"""

UNICODE_CHARSET="utf-8"

BSTR='b'
UNI='u'
LEN_SEP=':'
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
EXT='H'



identity = lambda x:x

def fail():
    raise StandardError()

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

    def dump(self, obj, resolver=identity, inline=fail):
        buf = StringIO()
        self._dump(obj, buf, resolver, inline)
        return buf.getvalue()

    def parse(self, s, resolver=identity):
        buf = StringIO(s)
        return self.read(buf, resolver)


    def _dump(self, obj, buf, resolver, inline):
        if obj is True:
            buf.write(TRUE)

        elif obj is False:
            buf.write(FALSE)
        
        elif obj is None:
            buf.write(NONE)
        
        elif isinstance(obj, (self.extension,)):
            buf.write(EXT)
            name, attributes, content = obj.__getstate__()
            obj.__resolve__(resolver)
            self._dump(name, buf, resolver, inline)
            self._dump(attributes, buf, resolver, inline)
            self._dump(content, buf, resolver, inline)
        
        elif isinstance(obj, (self.node,)):
            buf.write(NODE)
            name, attributes, content = obj.__getstate__()
            self._dump(name, buf, resolver, inline)
            self._dump(attributes, buf, resolver, inline)
            self._dump(content, buf, resolver, inline)
        
        elif isinstance(obj, (str, buffer)):
            buf.write(BSTR)
            buf.write("%d"%len(obj))
            buf.write(LEN_SEP)
            buf.write(obj)
        
        elif isinstance(obj, unicode):
            buf.write(UNI)
            obj = obj.encode(UNICODE_CHARSET)
            buf.write("%d"%len(obj))
            buf.write(LEN_SEP)
            buf.write(obj)
        
        elif isinstance(obj, set):
            buf.write(SET)
            for x in sorted(obj):
                self._dump(x, buf, resolver, inline)
            buf.write(END_SET)
        elif hasattr(obj, 'iteritems'):
            buf.write(DICT)
            for k in sorted(obj.keys()): # always sorted, so can compare serialized
                v=obj[k]
                self._dump(k, buf, resolver, inline)
                self._dump(v, buf, resolver, inline)
            buf.write(END_DICT)

        elif hasattr(obj, '__iter__'):
            buf.write(LIST)
            for x in obj:
                self._dump(x, buf, resolver, inline)
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
            buf.write(obj.strftime("%Y-%m-%dT%H:%M:%S.%fZ"))
            buf.write(END_ITEM)
        else:
            self._dump(inline(obj), buf, resolver, inline)


    def _read_one(self, fh, c, resolver):
        if c == NONE:
            return None
        elif c == TRUE:
            return True
        elif c == FALSE:
            return False
        if c == BSTR or c == UNI:
            l = _read_until(fh, LEN_SEP, parse=int)[0]
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
            ext.__resolve__(resolver)
            return ext
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

