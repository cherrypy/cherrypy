import logging
import sys

from cherrypy import config


class Application:
    """A CherryPy Application."""
    
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


class Tree:
    """A registry of CherryPy applications, mounted at diverse points."""
    
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

