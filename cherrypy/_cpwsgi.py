"""WSGI interface (see PEP 333)."""

import sys
import cherrypy
from cherrypy import _cpwsgiserver
from cherrypy._cperror import format_exc, bare_error
from cherrypy.lib import http


headerNames = {'HTTP_CGI_AUTHORIZATION': 'Authorization',
               'CONTENT_LENGTH': 'Content-Length',
               'CONTENT_TYPE': 'Content-Type',
               'REMOTE_HOST': 'Remote-Host',
               'REMOTE_ADDR': 'Remote-Addr',
               }

def translate_headers(environ):
    """Translate CGI-environ header names to HTTP header names."""
    for cgiName in environ:
        # We assume all incoming header keys are uppercase already.
        if cgiName in headerNames:
            yield headerNames[cgiName], environ[cgiName]
        elif cgiName[:5] == "HTTP_":
            # Hackish attempt at recovering original header names.
            translatedHeader = cgiName[5:].replace("_", "-")
            yield translatedHeader, environ[cgiName]


def _wsgi_callable(environ, start_response, app):
    request = None
    try:
        env = environ.get
        local = http.Host('', int(env('SERVER_PORT', 80)),
                          env('SERVER_NAME', ''))
        remote = http.Host(env('REMOTE_ADDR', ''),
                           int(env('REMOTE_PORT', -1)),
                           env('REMOTE_HOST', ''))
        request = cherrypy.engine.request(local, remote,
                                          env('wsgi.url_scheme'),
                                          env('ACTUAL_SERVER_PROTOCOL', "HTTP/1.1"))
        
        # LOGON_USER is served by IIS, and is the name of the
        # user after having been mapped to a local account.
        # Both IIS and Apache set REMOTE_USER, when possible.
        request.login = env('LOGON_USER') or env('REMOTE_USER') or None
        
        request.multithread = environ['wsgi.multithread']
        request.multiprocess = environ['wsgi.multiprocess']
        request.wsgi_environ = environ
        
        request.app = app
        
        path = env('SCRIPT_NAME', '') + env('PATH_INFO', '')
        response = request.run(environ['REQUEST_METHOD'], path,
                               env('QUERY_STRING'),
                               env('SERVER_PROTOCOL'),
                               translate_headers(environ),
                               environ['wsgi.input'])
        s, h, b = response.status, response.header_list, response.body
        exc = None
    except (KeyboardInterrupt, SystemExit), ex:
        try:
            if request:
                request.close()
        except:
            cherrypy.log(traceback=True)
        request = None
        raise ex
    except:
        if request and request.throw_errors:
            raise
        tb = format_exc()
        cherrypy.log(tb)
        if request and not request.show_tracebacks:
            tb = ""
        s, h, b = bare_error(tb)
        exc = sys.exc_info()
    
    try:
        start_response(s, h, exc)
        for chunk in b:
            # WSGI requires all data to be of type "str". This coercion should
            # not take any time at all if chunk is already of type "str".
            # If it's unicode, it could be a big performance hit (x ~500).
            if not isinstance(chunk, str):
                chunk = chunk.encode("ISO-8859-1")
            yield chunk
        if request:
            request.close()
        request = None
    except (KeyboardInterrupt, SystemExit), ex:
        try:
            if request:
                request.close()
        except:
            cherrypy.log(traceback=True)
        request = None
        raise ex
    except:
        cherrypy.log(traceback=True)
        try:
            if request:
                request.close()
        except:
            cherrypy.log(traceback=True)
        request = None
        s, h, b = bare_error()
        # CherryPy test suite expects bare_error body to be output,
        # so don't call start_response (which, according to PEP 333,
        # may raise its own error at that point).
        for chunk in b:
            if not isinstance(chunk, str):
                chunk = chunk.encode("ISO-8859-1")
            yield chunk


#                            Server components                            #


class CPHTTPRequest(_cpwsgiserver.HTTPRequest):
    
    def parse_request(self):
        mhs = cherrypy.server.max_request_header_size
        if mhs > 0:
            self.rfile = http.SizeCheckWrapper(self.rfile, mhs)
        
        try:
            _cpwsgiserver.HTTPRequest.parse_request(self)
        except http.MaxSizeExceeded:
            self.simple_response("413 Request Entity Too Large")
            cherrypy.log(traceback=True)
    
    def decode_chunked(self):
        """Decode the 'chunked' transfer coding."""
        if isinstance(self.rfile, http.SizeCheckWrapper):
            self.rfile = self.rfile.rfile
        mbs = cherrypy.server.max_request_body_size
        if mbs > 0:
            self.rfile = http.SizeCheckWrapper(self.rfile, mbs)
        try:
            return _cpwsgiserver.HTTPRequest.decode_chunked(self)
        except http.MaxSizeExceeded:
            self.simple_response("413 Request Entity Too Large")
            cherrypy.log(traceback=True)
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
        server = cherrypy.server
        sockFile = server.socket_file
        if sockFile:
            bind_addr = sockFile
        else:
            bind_addr = (server.socket_host, server.socket_port)
        
        s = _cpwsgiserver.CherryPyWSGIServer
        # We could just pass cherrypy.tree, but by passing tree.apps,
        # we get correct SCRIPT_NAMEs as early as possible.
        s.__init__(self, bind_addr, cherrypy.tree.apps.items(),
                   server.thread_pool,
                   server.socket_host,
                   request_queue_size = server.socket_queue_size,
                   timeout = server.socket_timeout,
                   )
        s.protocol = server.protocol_version

