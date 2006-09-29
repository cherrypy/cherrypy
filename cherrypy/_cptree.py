"""CherryPy Application and Tree objects."""

import os
import sys
import cherrypy
from cherrypy import _cpconfig, _cplogging, tools
from cherrypy._cperror import format_exc, bare_error
from cherrypy.lib import http


class Application(object):
    """A CherryPy Application.
    
    An instance of this class may also be used as a WSGI callable
    (WSGI application object) for itself.
    
    root: the top-most container of page handlers for this app.
    script_name: the URL "mount point" for this app; for example,
        if script_name is "/my/cool/app", then the URL
        "http://my.domain.tld/my/cool/app/page1" might be handled
        by a "page1" method on the root object. If script_name is
        explicitly set to None, then CherryPy will attempt to provide
        it each time from request.wsgi_environ['SCRIPT_NAME'].
    config: a dict of {path: pathconf} pairs, where 'pathconf' is itself
        a dict of {key: value} pairs.
    """
    
    def __init__(self, root, script_name=""):
        self.log = _cplogging.LogManager(id(self))
        self.root = root
        self.script_name = script_name
        self.namespaces = {"log": lambda k, v: setattr(self.log, k, v),
                           }
        self.config = {}
    
    def _get_script_name(self):
        if self._script_name is None:
            # None signals that the script name should be pulled from WSGI environ.
            return cherrypy.request.wsgi_environ['SCRIPT_NAME']
        return self._script_name
    def _set_script_name(self, value):
        self._script_name = value
    script_name = property(fget=_get_script_name, fset=_set_script_name)
    
    def merge(self, config):
        """Merge the given config into self.config."""
        _cpconfig.merge(self.config, config)
        
        # Handle namespaces specified in config.
        rootconf = self.config.get("/", {})
        for k, v in rootconf.iteritems():
            atoms = k.split(".", 1)
            namespace = atoms[0]
            if namespace in self.namespaces:
                self.namespaces[namespace](atoms[1], v)
    
    def wsgiapp(self, environ, start_response):
        # This is here instead of __call__ because it's really hard
        # to overwrite special methods like __call__ per instance.
        return wsgi_handler(environ, start_response, app=self)
    
    def __call__(self, environ, start_response):
        return self.wsgiapp(environ, start_response)


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


def wsgi_handler(environ, start_response, app):
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
                               env('QUERY_STRING', ''),
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


class Tree(object):
    """A registry of CherryPy applications, mounted at diverse points.
    
    An instance of this class may also be used as a WSGI callable
    (WSGI application object), in which case it dispatches to all
    mounted apps.
    
    apps: a dict of the form {script name: application}, where "script name"
        is a string declaring the URL mount point (no trailing slash),
        and "application" is an instance of cherrypy.Application (or an
        arbitrary WSGI callable if you happen to be using a WSGI server).
    """
    
    def __init__(self):
        self.apps = {}
    
    def mount(self, root, script_name="", config=None):
        """Mount a new app from a root object, script_name, and config."""
        # Next line both 1) strips trailing slash and 2) maps "/" -> "".
        script_name = script_name.rstrip("/")
        
        if isinstance(root, Application):
            app = root
        else:
            app = Application(root, script_name)
            
            # If mounted at "", add favicon.ico
            if script_name == "" and root and not hasattr(root, "favicon_ico"):
                favicon = os.path.join(os.getcwd(), os.path.dirname(__file__),
                                       "favicon.ico")
                root.favicon_ico = tools.staticfile.handler(favicon)
        
        if config:
            app.merge(config)
        
        self.apps[script_name] = app
        
        return app
    
    def graft(self, wsgi_callable, script_name=""):
        """Mount a wsgi callable at the given script_name."""
        # Next line both 1) strips trailing slash and 2) maps "/" -> "".
        script_name = script_name.rstrip("/")
        self.apps[script_name] = wsgi_callable
    
    def script_name(self, path=None):
        """The script_name of the app at the given path, or None.
        
        If path is None, cherrypy.request is used.
        """
        
        if path is None:
            try:
                path = cherrypy.request.script_name + cherrypy.request.path_info
            except AttributeError:
                return None
        
        while True:
            if path in self.apps:
                return path
            
            if path == "":
                return None
            
            # Move one node up the tree and try again.
            path = path[:path.rfind("/")]
    
    def __call__(self, environ, start_response):
        # If you're calling this, then you're probably setting SCRIPT_NAME
        # to '' (some WSGI servers always set SCRIPT_NAME to '').
        # Try to look up the app using the full path.
        path = environ.get('SCRIPT_NAME', '') + environ.get('PATH_INFO', '')
        sn = self.script_name(path or "/")
        if sn is None:
            start_response('404 Not Found', [])
            return []
        
        app = self.apps[sn]
        
        # Correct the SCRIPT_NAME and PATH_INFO environ entries.
        environ = environ.copy()
        environ['SCRIPT_NAME'] = sn
        environ['PATH_INFO'] = path[len(sn.rstrip("/")):]
        return app(environ, start_response)

