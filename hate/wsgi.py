import threading
import socket

from werkzeug.serving import make_server, WSGIRequestHandler

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
