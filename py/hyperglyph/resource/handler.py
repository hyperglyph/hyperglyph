import types
import sys
import collections

from werkzeug.wrappers import Response
from werkzeug.exceptions import HTTPException, NotFound, BadRequest, NotImplemented, MethodNotAllowed
from werkzeug.utils import redirect as Redirect
from werkzeug.datastructures import ResponseCacheControl

from ..data import CONTENT_TYPE, dump, parse, get, form, link, embedlink,  ismethod, methodargs


def get_stream(request):
    if request.headers.get('Transfer-Encoding') == 'chunked':
        raise StandardError('middleware doesnt unwrap transfer-encoding')
    else:
        return request.stream

class Handler(object):   
    """ Represents the capabilities of methods on resources, used by the mapper
        to determine how to handle requests
    """
    SAFE = False
    EMBED = False
    EXPIRES = False
    REDIRECT = None
    VISIBLE = True
    CACHE = ResponseCacheControl()

    def __init__(self, handler=None):
        if handler:
            self.safe = handler.safe
            self.embed = handler.embed
            self.expires = handler.expires
            self.cache = handler.cache
            self.visible = handler.visible
        else:
            self.safe = self.SAFE
            self.embed = self.EMBED
            self.redirect = self.REDIRECT
            self.cache = self.CACHE
            self.visible = self.VISIBLE

    @staticmethod
    def parse(resource, data):
        return parse(data)
    
    @staticmethod
    def dump(resource, data, resolver, inline):
        return CONTENT_TYPE, dump(data, resolver,inline)

    @classmethod
    def is_safe(cls, m):
        try:
            return m.__glyph_method__.safe
        except StandardError:
            if m.__name__ == 'GET':
                return True
            return cls.SAFE

    @classmethod
    def is_embed(cls, m):
        try:
            return m.__glyph_method__.embed
        except StandardError:
            return cls.EMBED

    @classmethod
    def is_redirect(cls, m):
        try:
            return m.__glyph_method__.redirect is not None
        except StandardError:
            return cls.REDIRECT

    @classmethod
    def is_visible(cls, m, name):
        try:
            return m.__glyph_method__.visible
        except StandardError:
            return not name.startswith('_')

    @staticmethod
    def redirect_code(m):
        return m.__glyph_method__.redirect

    @classmethod
    def make_link(cls, m):
        if cls.is_safe(m):
            if cls.is_embed(m):
                return embedlink(m,content=m())
            else:
                return link(m)
        else:
            return form(m)


    @classmethod
    def call(cls, attr, request, router):
        verb = request.method
        if verb == 'GET' and cls.is_safe(attr):
            result = attr()
        elif verb == 'POST' and not cls.is_safe(attr):
            try:
                data = collections.OrderedDict(cls.parse(attr, get_stream(request)))
            except StandardError:
                raise
                raise BadRequest()
            result =attr(**data)
        else:
            raise MethodNotAllowed()

        if result is None:
            return Response('', status='204 None')

        else:
            if cls.is_redirect(attr):
                try:
                    url = router.url(result)
                except LookupError:
                    pass
                else:
                    return Redirect(url, code=cls.redirect_code(attr))

            content_type, result = cls.dump(attr, result, router.url, router.inline)
            return Response(result, content_type=content_type)



def make_handler(fn):
    if not hasattr(fn, '__glyph_method__'):
        fn.__glyph_method__ = Handler() 
    return fn.__glyph_method__


def redirect(code=303):
    def _decorate(fn):
        m = make_handler(fn)
        m.redirect=code
        return fn
    return _decorate

def safe(embed=False):
    def _decorate(fn):
        m = make_handler(fn)
        m.safe=True
        m.embed=embed
        return fn
    return _decorate

def embed():
    return safe(embed=True)

def hidden():
    def _decorate(fn):
        m = make_handler(fn)
        m.visible = False
        return fn
    return _decorate
    
