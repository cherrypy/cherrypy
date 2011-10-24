"""WSGI server interface (see PEP 333). This adds some CP-specific bits to
the framework-agnostic cheroot package.
"""
import sys

import cherrypy
from cheroot import wsgi, ssllib


class CPWSGIServer(wsgi.WSGIServer):
    
    def __init__(self, server_adapter=cherrypy.server):
        self.server_adapter = server_adapter
        self.max_request_header_size = self.server_adapter.max_request_header_size or 0
        self.max_request_body_size = self.server_adapter.max_request_body_size or 0
        
        server_name = (self.server_adapter.socket_host or
                       self.server_adapter.socket_file or
                       None)
        
        self.wsgi_version = self.server_adapter.wsgi_version
        s = wsgi.WSGIServer
        s.__init__(self, server_adapter.bind_addr,
                   minthreads=self.server_adapter.thread_pool,
                   maxthreads=self.server_adapter.thread_pool_max,
                   server_name=server_name,
                   protocol = self.server_adapter.protocol_version,
                   )
        self.wsgi_app = cherrypy.tree
        self.request_queue_size = self.server_adapter.socket_queue_size
        self.timeout = self.server_adapter.socket_timeout
        self.shutdown_timeout = self.server_adapter.shutdown_timeout
        self.nodelay = self.server_adapter.nodelay

        if sys.version_info >= (3, 0):
            ssl_module = self.server_adapter.ssl_module or 'builtin'
        else:
            ssl_module = self.server_adapter.ssl_module or 'pyopenssl'
        if self.server_adapter.ssl_context:
            adapter_class = ssllib.get_ssl_adapter_class(ssl_module)
            self.ssl_adapter = adapter_class(
                self.server_adapter.ssl_certificate,
                self.server_adapter.ssl_private_key,
                self.server_adapter.ssl_certificate_chain)
            self.ssl_adapter.context = self.server_adapter.ssl_context
        elif self.server_adapter.ssl_certificate:
            adapter_class = ssllib.get_ssl_adapter_class(ssl_module)
            self.ssl_adapter = adapter_class(
                self.server_adapter.ssl_certificate,
                self.server_adapter.ssl_private_key,
                self.server_adapter.ssl_certificate_chain)
        
        self.stats['Enabled'] = getattr(self.server_adapter, 'statistics', False)

    def error_log(self, msg="", level=20, traceback=False):
        cherrypy.engine.log(msg, level, traceback)

