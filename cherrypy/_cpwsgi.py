"""WSGI interface (see PEP 333)."""

import cherrypy as _cherrypy
from cherrypy import _cpwsgiserver
from cherrypy.lib import http as _http


class pipeline(list):
    """An ordered list of configurable WSGI middleware.
    
    self: a list of (name, wsgiapp) pairs. Each 'wsgiapp' MUST be a
        constructor that takes an initial, positional wsgiapp argument,
        plus optional keyword arguments, and returns a WSGI application
        (that takes environ and start_response arguments). The 'name' can
        be any you choose, and will correspond to keys in self.config.
    config: a dict whose keys match names listed in the pipeline. Each
        value is a further dict which will be passed to the corresponding
        named WSGI callable (from the pipeline) as keyword arguments.
    """
    
    def __new__(cls, app, members=None, key="wsgi"):
        return list.__new__(cls)
    
    def __init__(self, app, members=None, key="wsgi"):
        self.app = app
        if members:
            self.extend(members)
        self.head = None
        self.tail = None
        self.config = {}
        self.key = key
        app.namespaces[key] = self.namespace_handler
        app.wsgi_pipeline = self
    
    def namespace_handler(self, k, v):
        """Config handler for our namespace."""
        if k == "pipeline":
            # Note this allows multiple entries to be aggregated (but also
            # note dicts are essentially unordered). It should also allow
            # developers to set default middleware in code (passed to
            # pipeline.__init__) that deployers can add to but not remove.
            self.extend(v)
            
            if self:
                # If self is empty, there's no need to replace app.wsgiapp.
                # Also note we're grabbing app.wsgiapp, not app.__call__,
                # so we can "play nice" with other Application-manglers
                # (hopefully, they'll do the same).
                self.tail = self.app.wsgiapp
                self.app.wsgiapp = self.__call__
        else:
            name, arg = k.split(".", 1)
            bucket = self.config.setdefault(name, {})
            bucket[arg] = v
    
    def __call__(self, environ, start_response):
        if not self.head:
            # This class may be used without calling namespace_handler,
            # in which case self.tail may still be None.
            self.head = self.tail or self.app.wsgiapp
            pipe = self[:]
            pipe.reverse()
            for name, callable in pipe:
                conf = self.config.get(name, {})
                self.head = callable(self.head, **conf)
        return self.head(environ, start_response)
    
    def __repr__(self):
        return "%s.%s(%r)" % (self.__module__, self.__class__.__name__,
                              list(self))



#                            Server components                            #


class CPHTTPRequest(_cpwsgiserver.HTTPRequest):
    
    def parse_request(self):
        mhs = _cherrypy.server.max_request_header_size
        if mhs > 0:
            self.rfile = _http.SizeCheckWrapper(self.rfile, mhs)
        
        try:
            _cpwsgiserver.HTTPRequest.parse_request(self)
        except _http.MaxSizeExceeded:
            self.simple_response("413 Request Entity Too Large")
            _cherrypy.log(traceback=True)
    
    def decode_chunked(self):
        """Decode the 'chunked' transfer coding."""
        if isinstance(self.rfile, _http.SizeCheckWrapper):
            self.rfile = self.rfile.rfile
        mbs = _cherrypy.server.max_request_body_size
        if mbs > 0:
            self.rfile = _http.SizeCheckWrapper(self.rfile, mbs)
        try:
            return _cpwsgiserver.HTTPRequest.decode_chunked(self)
        except _http.MaxSizeExceeded:
            self.simple_response("413 Request Entity Too Large")
            _cherrypy.log(traceback=True)
            return False


class CPHTTPConnection(_cpwsgiserver.HTTPConnection):
    
    RequestHandlerClass = CPHTTPRequest


class WSGIServer(_cpwsgiserver.CherryPyWSGIServer):
    
    """Wrapper for _cpwsgiserver.CherryPyWSGIServer.
    
    _cpwsgiserver has been designed to not reference CherryPy in any way,
    so that it can be used in other frameworks and applications. Therefore,
    we wrap it here, so we can set our own mount points from cherrypy.tree.
    
    """
    
    ConnectionClass = CPHTTPConnection
    
    def __init__(self):
        server = _cherrypy.server
        sockFile = server.socket_file
        if sockFile:
            bind_addr = sockFile
        else:
            bind_addr = (server.socket_host, server.socket_port)
        
        s = _cpwsgiserver.CherryPyWSGIServer
        # We could just pass cherrypy.tree, but by passing tree.apps,
        # we get correct SCRIPT_NAMEs as early as possible.
        s.__init__(self, bind_addr, _cherrypy.tree.apps.items(),
                   server.thread_pool,
                   server.socket_host,
                   request_queue_size = server.socket_queue_size,
                   timeout = server.socket_timeout,
                   )
        s.protocol = server.protocol_version

