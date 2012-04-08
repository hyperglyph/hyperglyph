import types

from werkzeug.wrappers import Response
from werkzeug.exceptions import HTTPException, NotFound, BadRequest, NotImplemented, MethodNotAllowed
from werkzeug.utils import redirect as Redirect
from werkzeug.datastructures import ResponseCacheControl

from ..data import CONTENT_TYPE, dump, parse, get, form, link, node, embed, ismethod, methodargs

VERBS = set(("GET", "POST", "PUT","DELETE","PATCH",))
class Handler(object):   
    """ Represents the capabilities of methods on resources, used by the mapper
        to determine how to handle requests
    """
    SAFE=False
    INLINE=False
    EXPIRES=False
    REDIRECT=None
    CACHE=ResponseCacheControl()

    def __init__(self, handler=None):
        if handler:
            self.safe=handler.safe
            self.inline=handler.inline
            self.expires=handler.expires
            self.cache=handler.cache
        else:
            self.safe=self.SAFE
            self.inline=self.INLINE
            self.redirect=self.REDIRECT
            self.cache=self.CACHE

    @staticmethod
    def parse(resource, data):
        return parse(data)
    
    @staticmethod
    def dump(resource, data, resolver):
        return CONTENT_TYPE, dump(data, resolver)

    @classmethod
    def is_safe(cls, m):
        try:
            return m.__glyph_method__.safe
        except StandardError:
            if m.__name__ == 'GET':
                return True
            return cls.SAFE

    @classmethod
    def is_inline(cls, m):
        try:
            return m.__glyph_method__.inline
        except StandardError:
            return cls.INLINE

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
            if cls.is_inline(m):
                return embed(m,content=m())
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
                data = cls.parse(attr, request.data) if request.data else {}
            except StandardError:
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

            content_type, result = cls.dump(attr, result, router.url)
            return Response(result, content_type=content_type)

def make_controls(resource):
    forms = {}
    for m in dir(resource.__class__):
        if not m.startswith('_') and m not in VERBS and m != 'index':
            cls_attr = getattr(resource.__class__ ,m)
            ins_attr = getattr(resource,m)


            if isinstance(cls_attr, property):
                forms[m] = ins_attr
            elif callable(cls_attr):
                if hasattr(ins_attr, 'func_code'):
                    forms[m] = Handler.make_link(ins_attr)

    return forms


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

def safe(inline=False):
    def _decorate(fn):
        m = make_handler(fn)
        m.safe=True
        m.inline=inline
        return fn
    return _decorate

def inline():
    return safe(inline=True)

