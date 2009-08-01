"""WSGI server interface (see PEP 333). This adds some CP-specific bits to
the framework-agnostic wsgiserver package.
"""
import sys

import cherrypy
from cherrypy import wsgiserver


class CPHTTPRequest(wsgiserver.HTTPRequest):
    
    def __init__(self, sendall, environ, wsgi_app):
        s = cherrypy.server
        self.max_request_header_size = s.max_request_header_size or 0
        self.max_request_body_size = s.max_request_body_size or 0
        wsgiserver.HTTPRequest.__init__(self, sendall, environ, wsgi_app)


class CPHTTPConnection(wsgiserver.HTTPConnection):
    
    RequestHandlerClass = CPHTTPRequest


class CPWSGIServer(wsgiserver.CherryPyWSGIServer):
    """Wrapper for wsgiserver.CherryPyWSGIServer.
    
    wsgiserver has been designed to not reference CherryPy in any way,
    so that it can be used in other frameworks and applications. Therefore,
    we wrap it here, so we can set our own mount points from cherrypy.tree
    and apply some attributes from config -> cherrypy.server -> wsgiserver.
    """
    
    ConnectionClass = CPHTTPConnection
    
    def __init__(self, server_adapter=cherrypy.server):
        self.server_adapter = server_adapter
        
        # We have to make custom subclasses of wsgiserver internals here
        # so that our server.* attributes get applied to every request.
        class _CPHTTPRequest(wsgiserver.HTTPRequest):
            def __init__(self, sendall, environ, wsgi_app):
                s = server_adapter
                self.max_request_header_size = s.max_request_header_size or 0
                self.max_request_body_size = s.max_request_body_size or 0
                wsgiserver.HTTPRequest.__init__(self, sendall, environ, wsgi_app)
        class _CPHTTPConnection(wsgiserver.HTTPConnection):
            RequestHandlerClass = _CPHTTPRequest
        self.ConnectionClass = _CPHTTPConnection
        
        server_name = (self.server_adapter.socket_host or
                       self.server_adapter.socket_file or
                       None)
        
        s = wsgiserver.CherryPyWSGIServer
        s.__init__(self, server_adapter.bind_addr, cherrypy.tree,
                   self.server_adapter.thread_pool,
                   server_name,
                   max = self.server_adapter.thread_pool_max,
                   request_queue_size = self.server_adapter.socket_queue_size,
                   timeout = self.server_adapter.socket_timeout,
                   shutdown_timeout = self.server_adapter.shutdown_timeout,
                   )
        self.protocol = self.server_adapter.protocol_version
        self.nodelay = self.server_adapter.nodelay
        
        if self.server_adapter.ssl_context:
            adapter_class = self.get_ssl_adapter_class()
            s.ssl_adapter = adapter_class(self.server_adapter.ssl_certificate,
                                          self.server_adapter.ssl_private_key,
                                          self.server_adapter.ssl_certificate_chain)
            s.ssl_adapter.context = self.server_adapter.ssl_context
        elif self.server_adapter.ssl_certificate:
            adapter_class = self.get_ssl_adapter_class()
            s.ssl_adapter = adapter_class(self.server_adapter.ssl_certificate,
                                          self.server_adapter.ssl_private_key,
                                          self.server_adapter.ssl_certificate_chain)
    
    def get_ssl_adapter_class(self):
        adname = (self.server_adapter.ssl_module or 'pyopenssl').lower()
        adapter = ssl_adapters[adname]
        if isinstance(adapter, basestring):
            last_dot = adapter.rfind(".")
            attr_name = adapter[last_dot + 1:]
            mod_path = adapter[:last_dot]
            
            try:
                mod = sys.modules[mod_path]
                if mod is None:
                    raise KeyError()
            except KeyError:
                # The last [''] is important.
                mod = __import__(mod_path, globals(), locals(), [''])
            
            # Let an AttributeError propagate outward.
            try:
                adapter = getattr(mod, attr_name)
            except AttributeError:
                raise AttributeError("'%s' object has no attribute '%s'"
                                     % (mod_path, attr_name))
        
        return adapter

# These may either be wsgiserver.SSLAdapter subclasses or the string names
# of such classes (in which case they will be lazily loaded).
ssl_adapters = {
    'builtin': 'cherrypy.wsgiserver.ssl_builtin.BuiltinSSLAdapter',
    'pyopenssl': 'cherrypy.wsgiserver.ssl_pyopenssl.pyOpenSSLAdapter',
    }

