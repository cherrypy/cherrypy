import logging

from cherrypy import config, _cpwsgi


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
    conf: a dict of {path: pathconf} pairs, where 'pathconf' is itself
        a dict of {key: value} pairs.
    """
    
    def __init__(self, root, script_name="", conf=None):
        self.access_log = log = logging.getLogger("cherrypy.access.%s" % id(self))
        log.setLevel(logging.INFO)
        
        self.error_log = log = logging.getLogger("cherrypy.error.%s" % id(self))
        log.setLevel(logging.DEBUG)
        
        self.root = root
        self.script_name = script_name
        self.conf = {}
        if conf:
            self.merge(conf)
    
    def _get_script_name(self):
        if self._script_name is None:
            # None signals that the script name should be pulled from WSGI environ.
            import cherrypy
            return cherrypy.request.wsgi_environ['SCRIPT_NAME']
        return self._script_name
    def _set_script_name(self, value):
        self._script_name = value
    script_name = property(fget=_get_script_name, fset=_set_script_name)
    
    def merge(self, conf):
        """Merge the given config into self.config."""
        config.merge(self.conf, conf)
        
        # Create log handlers as specified in config.
        rootconf = self.conf.get("/", {})
        config._configure_builtin_logging(rootconf, self.access_log, "log_access_file")
        config._configure_builtin_logging(rootconf, self.error_log)
    
    def guess_abs_path(self):
        """Guess the absolute URL from server.socket_host and script_name.
        
        When inside a request, the abs_path can be formed via:
            cherrypy.request.base + (cherrypy.request.app.script_name or "/")
        
        However, outside of the request we must guess, hoping the deployer
        set socket_host and socket_port correctly.
        """
        port = int(config.get('server.socket_port', 80))
        if port in (443, 8443):
            scheme = "https://"
        else:
            scheme = "http://"
        host = config.get('server.socket_host', '')
        if port != 80:
            host += ":%s" % port
        return scheme + host + self.script_name
    
    def __call__(self, environ, start_response):
        return _cpwsgi._wsgi_callable(environ, start_response, app=self)


class Tree:
    """A registry of CherryPy applications, mounted at diverse points.
    
    An instance of this class may also be used as a WSGI callable
    (WSGI application object), in which case it dispatches to all
    mounted apps.
    """
    
    def __init__(self):
        self.apps = {}
    
    def mount(self, root, script_name="", conf=None):
        """Mount a new app from a root object, script_name, and conf."""
        # Next line both 1) strips trailing slash and 2) maps "/" -> "".
        script_name = script_name.rstrip("/")
        app = Application(root, script_name, conf)
        self.apps[script_name] = app
        
        # If mounted at "", add favicon.ico
        if script_name == "" and root and not hasattr(root, "favicon_ico"):
            import os
            from cherrypy import tools
            favicon = os.path.join(os.getcwd(), os.path.dirname(__file__),
                                   "favicon.ico")
            root.favicon_ico = tools.staticfile.handler(favicon)
        
        return app
    
    def graft(self, wsgi_callable, script_name=""):
        """Mount a wsgi callable at the given script_name."""
        # Next line both 1) strips trailing slash and 2) maps "/" -> "".
        script_name = script_name.rstrip("/")
        self.apps[script_name] = wsgi_callable
    
    def script_name(self, path=None):
        """The script_name of the app at the given path, or None.
        
        If path is None, cherrypy.request.path is used.
        """
        
        if path is None:
            try:
                import cherrypy
                path = cherrypy.request.path
            except AttributeError:
                return None
        
        while True:
            if path in self.apps:
                return path
            
            if path == "":
                return None
            
            # Move one node up the tree and try again.
            path = path[:path.rfind("/")]
    
    def url(self, path, script_name=None):
        """Return 'path', prefixed with script_name.
        
        If script_name is None, cherrypy.request.path will be used
        to find a script_name.
        """
        
        if script_name is None:
            script_name = self.script_name()
            if script_name is None:
                return path
        
        from cherrypy.lib import http
        return http.urljoin(script_name, path)
    
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

