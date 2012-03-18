import weakref

from werkzeug.utils import redirect as Redirect
from werkzeug.wrappers import Request, Response
from werkzeug.exceptions import HTTPException, NotFound, BadRequest, NotImplemented, MethodNotAllowed


from .base import BaseMapper, BaseResource, get_mapper
from .handler import Handler, safe
from .transient import TransientResource
from ..data import ismethod


        

def make_default(router):
    class __default__(TransientResource):
        def index(self):
            return dict((r.__name__, Handler.make_link(r)) for r in router.mappers if r is not self.__class__) 
    return __default__
class Router(object):
    def __init__(self):
        self.mappers = {}
        self.routes = {}
        default = make_default(weakref.proxy(self))
    
        self.register(default)
        self.default_resource = default()

    def __call__(self, environ, start_response):
        request = Request(environ)
        try:
            if request.path == '/':
                response = Redirect(self.url(self.default_resource), code=303)
            else:
                response = self.find_mapper(request.path).handle(request, self)

        except (StopIteration, GeneratorExit, SystemExit, KeyboardInterrupt):
            raise
        except HTTPException as r:
            response = r
        except Exception as e:
            import traceback;
            traceback.print_exc()
            response = Response(traceback.format_exc(), status='500 not ok')
        return response(environ, start_response)


    def find_mapper(self, path):
        try:
            path= path[1:].split('/')
            return  self.routes[path[0]]
        except StandardError:
            raise NotFound()

    def register(self, obj):
        path = obj.__name__
        mapper = get_mapper(obj, path)
        self.routes[path] = mapper
        self.mappers[obj] = mapper
        return obj


    def url(self, r):
        if isinstance(r, basestring):
            return r
        elif isinstance(r, BaseResource):
            return self.mappers[r.__class__].url(r)
        elif ismethod(r, BaseResource):
            return self.mappers[r.im_class].url(r)
        elif r in self.mappers:
            return self.mappers[r].url(r)

        raise LookupError('no url for',r )

    def add(self):
        return self.register

    def default(self, **args):
        def _register(obj):
            self.register(obj)
            self.default_resource=obj(**args)
            return obj
        return _register

        
