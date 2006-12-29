"""A WSGI application interface (see PEP 333)."""

import sys
import cherrypy
from cherrypy import _cputil, _cpwsgiserver, _cpwsgiserver3
from cherrypy.lib import httptools


def requestLine(environ):
    """Rebuild first line of the request (e.g. "GET /path HTTP/1.0")."""
    
    resource = environ.get('SCRIPT_NAME', '') + environ.get('PATH_INFO', '')
    if not (resource == "*" or resource.startswith("/")):
        resource = "/" + resource
    
    qString = environ.get('QUERY_STRING')
    if qString:
        resource += '?' + qString
    
    resource = resource.replace(" ", "%20")
    
    return ('%s %s %s' % (environ['REQUEST_METHOD'],
                          resource or '/',
                          environ['SERVER_PROTOCOL']
                          )
            )

headerNames = {'HTTP_CGI_AUTHORIZATION': 'Authorization',
               'CONTENT_LENGTH': 'Content-Length',
               'CONTENT_TYPE': 'Content-Type',
               'REMOTE_HOST': 'Remote-Host',
               'REMOTE_ADDR': 'Remote-Addr',
               }

def translate_headers(environ):
    """Translate CGI-environ header names to HTTP header names."""
    for cgiName in environ:
        translatedHeader = headerNames.get(cgiName.upper())
        if translatedHeader:
            yield translatedHeader, environ[cgiName]
        elif cgiName.upper().startswith("HTTP_"):
            # Hackish attempt at recovering original header names.
            translatedHeader = cgiName[5:].replace("_", "-")
            yield translatedHeader, environ[cgiName]


class NullWriter(object):
    
    def write(self, data):
        pass

class ResponseIter(object):
    def __init__(self, request, body):
        self.body = body
        self.request = request
        
    def __iter__(self):
        if not self.body:
            raise StopIteration
        try:
            for chunk in self.body:
                # WSGI requires all data to be of type "str". This coercion should
                # not take any time at all if chunk is already of type "str".
                # If it's unicode, it could be a big performance hit (x ~500).
                if not isinstance(chunk, str):
                    chunk = chunk.encode("ISO-8859-1")
                yield chunk
        except (KeyboardInterrupt, SystemExit), ex:
            raise ex
        except:
            cherrypy.log(traceback=True)
            s, h, b = _cputil.bareError()
            # CherryPy test suite expects bareError body to be output,
            # so don't call start_response (which, according to PEP 333,
            # may raise its own error at that point).
            for chunk in b:
                # WSGI requires all data to be of type "str". This coercion should
                # not take any time at all if chunk is already of type "str".
                # If it's unicode, it could be a big performance hit (x ~500).
                if not isinstance(chunk, str):
                    chunk = chunk.encode("ISO-8859-1")
                yield chunk
    
    def close(self):
        try:
            if self.request:
                self.request.close()
        except:
            cherrypy.log(traceback=True)
        self.request = None

def wsgiApp(environ, start_response):
    """The WSGI 'application object' for CherryPy."""
    
    # Trap screen output from BaseHTTPRequestHandler.log_message()
    if not cherrypy.config.get('server.log_to_screen'):
        sys.stderr = NullWriter()
    
    request = None
    try:
        env = environ.get
        clientAddr = (env('REMOTE_ADDR', ''), int(env('REMOTE_PORT', -1)))
        request = cherrypy.server.request(clientAddr, '', environ['wsgi.url_scheme'])
        
        # LOGON_USER is served by IIS, and is the name of the
        # user after having been mapped to a local account.
        # Both IIS and Apache set REMOTE_USER, when possible.
        request.login = (env('LOGON_USER') or env('REMOTE_USER') or None)
        
        request.multithread = environ['wsgi.multithread']
        request.multiprocess = environ['wsgi.multiprocess']
        request.wsgi_environ = environ
        response = request.run(requestLine(environ),
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
        if cherrypy.config.get("server.throw_errors", False):
            if request:
                request.close()
                request = None
            raise
        tb = _cputil.formatExc()
        cherrypy.log(tb)
        if not cherrypy.config.get("server.show_tracebacks", False):
            tb = ""
        s, h, b = _cputil.bareError(tb)
        exc = sys.exc_info()
    
    start_response(s, h, exc)
    return ResponseIter(request, b)




# Server components.


class CPHTTPRequest(_cpwsgiserver.HTTPRequest):
    
    def __init__(self, socket, addr, server):
        _cpwsgiserver.HTTPRequest.__init__(self, socket, addr, server)
        mhs = int(cherrypy.config.get('server.max_request_header_size',
                                      500 * 1024))
        if mhs > 0:
            self.rfile = httptools.SizeCheckWrapper(self.rfile, mhs)
    
    def parse_request(self):
        try:
            _cpwsgiserver.HTTPRequest.parse_request(self)
        except httptools.MaxSizeExceeded:
            msg = "Request Entity Too Large"
            proto = self.environ.get("SERVER_PROTOCOL", "HTTP/1.0")
            self.wfile.write("%s 413 %s\r\n" % (proto, msg))
            self.wfile.write("Content-Length: %s\r\n\r\n" % len(msg))
            self.wfile.write(msg)
            self.wfile.flush()
            self.ready = False
            
            cherrypy.log(traceback=True)
        else:
            if self.ready:
                if isinstance(self.rfile, httptools.SizeCheckWrapper):
                    # Unwrap the rfile
                    self.rfile = self.rfile.rfile
                self.environ["wsgi.input"] = self.rfile


class WSGIServer(_cpwsgiserver.CherryPyWSGIServer):
    
    """Wrapper for _cpwsgiserver.CherryPyWSGIServer.
    
    _cpwsgiserver has been designed to not reference CherryPy in any way,
    so that it can be used in other frameworks and applications. Therefore,
    we wrap it here, so we can set our own mount points from cherrypy.tree.
    
    """
    
    RequestHandlerClass = CPHTTPRequest
    
    def __init__(self):
        conf = cherrypy.config.get
        
        sockFile = cherrypy.config.get('server.socket_file')
        if sockFile:
            bind_addr = sockFile
        else:
            bind_addr = (conf("server.socket_host"), conf("server.socket_port"))
        
        pts = cherrypy.tree.mount_points
        if pts:
            apps = [(base, wsgiApp) for base in pts.keys()]
        else:
            apps = [("", wsgiApp)]
        
        s = _cpwsgiserver.CherryPyWSGIServer
        s.__init__(self, bind_addr, apps,
                   conf("server.thread_pool"),
                   conf("server.socket_host"),
                   request_queue_size = conf('server.socket_queue_size'),
                   timeout = conf('server.socket_timeout'),
                   )


#                            Server3 components                            #


class CPHTTPRequest3(_cpwsgiserver3.HTTPRequest):
    
    def parse_request(self):
        mhs = int(cherrypy.config.get('server.max_request_header_size',
                                      500 * 1024))
        if mhs > 0:
            self.rfile = httptools.SizeCheckWrapper(self.rfile, mhs)
        
        try:
            _cpwsgiserver3.HTTPRequest.parse_request(self)
        except httptools.MaxSizeExceeded:
            self.simple_response("413 Request Entity Too Large")
            cherrypy.log(traceback=True)
        else:
            if self.ready:
                if isinstance(self.rfile, httptools.SizeCheckWrapper):
                    # Unwrap the rfile
                    self.rfile = self.rfile.rfile
                self.environ["wsgi.input"] = self.rfile
    
    def decode_chunked(self):
        """Decode the 'chunked' transfer coding."""
        if isinstance(self.rfile, httptools.SizeCheckWrapper):
            self.rfile = self.rfile.rfile
        mbs = int(cherrypy.config.get('server.max_request_body_size',
                                      100 * 1024 * 1024))
        if mbs > 0:
            self.rfile = httptools.SizeCheckWrapper(self.rfile, mbs)
        try:
            return _cpwsgiserver3.HTTPRequest.decode_chunked(self)
        except httptools.MaxSizeExceeded:
            self.simple_response("413 Request Entity Too Large")
            cherrypy.log(traceback=True)
            return False


class CPHTTPConnection3(_cpwsgiserver3.HTTPConnection):
    
    RequestHandlerClass = CPHTTPRequest3


class CPWSGIServer3(_cpwsgiserver3.CherryPyWSGIServer):
    """Wrapper for _cpwsgiserver3.CherryPyWSGIServer.
    
    wsgiserver has been designed to not reference CherryPy in any way,
    so that it can be used in other frameworks and applications. Therefore,
    we wrap it here, so we can set our own mount points from cherrypy.tree.
    """
    
    ConnectionClass = CPHTTPConnection3
    
    def __init__(self):
        conf = cherrypy.config.get
        
        sockFile = cherrypy.config.get('server.socket_file')
        if sockFile:
            bind_addr = sockFile
        else:
            bind_addr = (conf("server.socket_host"), conf("server.socket_port"))
        
        pts = cherrypy.tree.mount_points
        if pts:
            apps = [(base, wsgiApp) for base in pts.keys()]
        else:
            apps = [("", wsgiApp)]
        
        s = _cpwsgiserver3.CherryPyWSGIServer
        s.__init__(self, bind_addr, apps,
                   conf("server.thread_pool"),
                   conf("server.socket_host"),
                   request_queue_size = conf('server.socket_queue_size'),
                   timeout = conf('server.socket_timeout'),
                   )
        
        self.protocol = conf("server.protocol_version")
        self.ssl_certificate = conf("server.ssl_certificate")
        self.ssl_private_key = conf("server.ssl_private_key")


