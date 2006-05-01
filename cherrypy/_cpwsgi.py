"""A WSGI application interface (see PEP 333)."""

import sys
import cherrypy
from cherrypy import _cputil, _cpwsgiserver
from cherrypy._cperror import format_exc, bare_error
from cherrypy.lib import httptools


def request_line(environ):
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


def wsgiApp(environ, start_response):
    """The WSGI 'application object' for CherryPy."""
    
    # Trap screen output from BaseHTTPRequestHandler.log_message()
    if not cherrypy.config.get('server.log_to_screen'):
        sys.stderr = NullWriter()
    
    request = None
    try:
        # LOGON_USER is served by IIS, and is the name of the
        # user after having been mapped to a local account.
        # Both IIS and Apache set REMOTE_USER, when possible.
        env = environ.get
        clientAddr = (env('REMOTE_ADDR', ''), int(env('REMOTE_PORT', -1)))
        request = cherrypy.server.request(clientAddr, env('REMOTE_ADDR', ''),
                                          environ['wsgi.url_scheme'])
        request.login = (env('LOGON_USER') or env('REMOTE_USER') or None)
        request.multithread = environ['wsgi.multithread']
        request.multiprocess = environ['wsgi.multiprocess']
        request.wsgi_environ = environ
        response = request.run(request_line(environ),
                               translate_headers(environ),
                               environ['wsgi.input'])
        s, h, b = response.status, response.header_list, response.body
        exc = None
    except (KeyboardInterrupt, SystemExit):
        raise
    except:
        if cherrypy.config.get("server.throw_errors", False):
            raise
        tb = format_exc()
        cherrypy.log(tb)
        if not cherrypy.config.get("server.show_tracebacks", False):
            tb = ""
        s, h, b = bare_error(tb)
        exc = sys.exc_info()
    
    try:
        start_response(s, h, exc)
        for chunk in b:
            # WSGI requires all data to be of type "str". This coercion should
            # not take any time at all if chunk is already of type "str".
            # If it's unicode, it could be a big performance hit (x ~500).
            chunk = str(chunk)
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
            yield str(chunk)


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
                # Request header is parsed
                script_name = self.environ.get('SCRIPT_NAME', '')
                path_info = self.environ.get('PATH_INFO', '')
                path = (script_name + path_info)
                if path == "*":
                    path = "global"
                
                # Prepare the SizeCheckWrapper for the request body
                mbs = int(cherrypy.config.get('server.max_request_body_size',
                                              100 * 1024 * 1024, path=path))
                if isinstance(self.rfile, httptools.SizeCheckWrapper):
                    if mbs > 0:
                        self.rfile.bytes_read = 0
                        self.rfile.maxlen = mbs
                    else:
                        # Unwrap the rfile
                        self.rfile = self.rfile.rfile
                else:
                    if mbs > 0:
                        self.rfile = httptools.SizeCheckWrapper(self.rfile, mbs)
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
                   )

