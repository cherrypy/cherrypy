"""CherryPy Application and Tree objects."""

import os
import cherrypy
from cherrypy import _cpconfig, _cplogging, _cpwsgi, tools


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
        self.wsgiapp = _cpwsgi.CPWSGIApp(self)
        self.namespaces = {"log": lambda k, v: setattr(self.log, k, v),
                           "wsgi": self.wsgiapp.namespace_handler,
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
        _cpconfig._call_namespaces(self.config.get("/", {}), self.namespaces)
    
    def __call__(self, environ, start_response):
        return self.wsgiapp(environ, start_response)


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

