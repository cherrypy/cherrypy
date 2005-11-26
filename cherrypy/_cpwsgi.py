"""A WSGI application interface (see PEP 333)."""

import sys
import cherrypy
from cherrypy import _cputil
from cherrypy._cpwsgiserver import CherryPyWSGIServer as server


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


def wsgiApp(environ, start_response):
    """The WSGI 'application object' for CherryPy."""
    
    # Trap screen output from BaseHTTPRequestHandler.log_message()
    if not cherrypy.config.get('server.logToScreen'):
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
        response = request.run(requestLine(environ),
                               translate_headers(environ),
                               environ['wsgi.input'])
        s, h, b = response.status, response.headers, response.body
        exc = None
    except (KeyboardInterrupt, SystemExit):
        raise
    except:
        tb = _cputil.formatExc()
        cherrypy.log(tb)
        if not cherrypy.config.get("server.showTracebacks", False):
            tb = ""
        s, h, b = _cputil.bareError(tb)
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
    except (KeyboardInterrupt, SystemExit):
        raise
    except:
        tb = _cputil.formatExc()
        cherrypy.log(tb)
        s, h, b = _cputil.bareError()
        # CherryPy test suite expects bareError body to be output,
        # so don't call start_response (which, according to PEP 333,
        # may raise its own error at that point).
        for chunk in b:
            yield str(chunk)



# Server components.

class WSGIServer(server):
    
    """Wrapper for _cpwsgiserver.CherryPyWSGIServer.
    
    _cpwsgiserver has been designed to not reference CherryPy in any way,
    so that it can be used in other frameworks and applications. Therefore,
    we wrap it here.
    
    """
    
    def __init__(self):
        conf = cherrypy.config.get
        server.__init__(self,
                        (conf("server.socketHost"), conf("server.socketPort")),
                        wsgiApp,
                        conf("server.threadPool"),
                        conf("server.socketHost"),
                        config = cherrypy.config
                        )
