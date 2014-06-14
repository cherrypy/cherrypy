"""WSGI server interface (see PEP 333). This adds some CP-specific bits to
the framework-agnostic cheroot package.
"""
import sys

import cherrypy
from cheroot import wsgi, ssllib


class CPWSGIServer(wsgi.WSGIServer):

    def __init__(self, server_adapter=cherrypy.server):
        self.server_adapter = server_adapter
        self.max_request_header_size = (
            server_adapter.max_request_header_size or 0
        )
        self.max_request_body_size = (
            server_adapter.max_request_body_size or 0
        )

        server_name = (
            server_adapter.socket_host or server_adapter.socket_file or None)

        self.wsgi_version = server_adapter.wsgi_version
        super(CPWSGIServer, self).__init__(
            server_adapter.bind_addr,
            minthreads=server_adapter.thread_pool,
            maxthreads=server_adapter.thread_pool_max,
            server_name=server_name,
            protocol=server_adapter.protocol_version,
            accepted_queue_size=server_adapter.accepted_queue_size,
            accepted_queue_timeout=server_adapter.accepted_queue_timeout
        )
        cherrypy.engine.threadpool_monitor.configure(self.requests,
                                                     server_adapter,
                                                     self.error_log)

        self.wsgi_app = cherrypy.tree
        self.request_queue_size = server_adapter.socket_queue_size
        self.timeout = server_adapter.socket_timeout
        self.shutdown_timeout = server_adapter.shutdown_timeout
        self.nodelay = server_adapter.nodelay

        if sys.version_info >= (3, 0):
            ssl_module = server_adapter.ssl_module or 'builtin'
        else:
            ssl_module = server_adapter.ssl_module or 'pyopenssl'
        if server_adapter.ssl_context or server_adapter.ssl_certificate:
            adapter_class = ssllib.get_ssl_adapter_class(ssl_module)
            self.ssl_adapter = adapter_class(
                server_adapter.ssl_certificate,
                server_adapter.ssl_private_key,
                server_adapter.ssl_certificate_chain)
            if server_adapter.ssl_context:
                self.ssl_adapter.context = server_adapter.ssl_context

        self.stats['Enabled'] = getattr(server_adapter, 'statistics', False)

    def error_log(self, msg="", level=20, traceback=False):
        cherrypy.engine.log(msg, level, traceback)
