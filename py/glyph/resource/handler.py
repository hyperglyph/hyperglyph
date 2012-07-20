import types

from werkzeug.wrappers import Response
from werkzeug.exceptions import HTTPException, NotFound, BadRequest, NotImplemented, MethodNotAllowed
from werkzeug.utils import redirect as Redirect
from werkzeug.datastructures import ResponseCacheControl

from ..data import CONTENT_TYPE, dump, parse, get, form, link, node, embedlink,  ismethod, methodargs

class Handler(object):   
    """ Represents the capabilities of methods on resources, used by the mapper
        to determine how to handle requests
    """
    SAFE=False
    EMBED=False
    EXPIRES=False
    REDIRECT=None
    CACHE=ResponseCacheControl()

    def __init__(self, handler=None):
        if handler:
            self.safe=handler.safe
            self.embed=handler.embed
            self.expires=handler.expires
            self.cache=handler.cache
        else:
            self.safe=self.SAFE
            self.embed=self.EMBED
            self.redirect=self.REDIRECT
            self.cache=self.CACHE

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
                data = dict(cls.parse(attr, request.input_stream))
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
