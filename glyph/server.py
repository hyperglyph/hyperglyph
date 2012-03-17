from werkzeug.wrappers import Request, Response
from werkzeug.exceptions import HTTPException, NotFound, BadRequest, NotImplemented, MethodNotAllowed
from werkzeug.utils import redirect as Redirect
import threading
import socket
import weakref

from werkzeug.serving import make_server, WSGIRequestHandler
from .resource.base import BaseMapper, BaseResource, get_mapper, Handler
from .resource.persistent import PersistentResource
from .data import ismethod


class DefaultResource(PersistentResource):
    def __init__(self, router):
        self.router = router

    def index(self):
        return dict((r.__name__, Handler.make_link(r)) for r in self.router.mappers if r is not DefaultResource) 
        

class Router(object):
    def __init__(self):
        self.mappers = {}
        self.routes = {}
        self.register(DefaultResource)
        self.default_resource = DefaultResource(weakref.proxy(self))

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

        


class RequestHandler(WSGIRequestHandler):
    def log_request(self, code='-', size='-'):
        pass

class Server(threading.Thread):
    def __init__(self, app, host="", port=0, threaded=True, processes=1,
                request_handler=RequestHandler, passthrough_errors=False, ssl_context=None):
        """ Use ssl_context='adhoc' for an ad-hoc cert, a tuple for a (cerk, pkey) files
            
        
        """
        threading.Thread.__init__(self)
        self.daemon=True
        self.server = make_server(host, port, app, threaded=threaded, processes=processes,
            request_handler=request_handler, passthrough_errors=passthrough_errors, ssl_context=ssl_context)

    @property
    def url(self):
        return 'http%s://%s:%d/'%(('s' if self.server.ssl_context else ''), self.server.server_name, self.server.server_port)

    def run(self):
        self.server.serve_forever()

    def stop(self):
        self.server.shutdown_signal = True
        if self.server and self.is_alive():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect((self.server.server_name, self.server.server_port))
                s.send('\r\n')
                s.close()
            except IOError:
                import traceback
                traceback.print_exc()
        self.join(5)
