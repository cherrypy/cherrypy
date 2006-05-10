
from cherrypy import config


class Application:
    
    def __init__(self, root, conf=None):
        self.root = root
        self.conf = {}
        if conf:
            self.merge(conf)
    
    def merge(self, conf):
        config.merge(self.conf, conf)


class Tree:
    """A registry of mounted applications at diverse points."""
    
    def __init__(self):
        self.apps = {}
    
    def mount(self, root, script_name=None, conf=None):
        """Mount a new app from a root object, script_name, and conf."""
        app = Application(root, conf)
        if script_name is None:
            script_name = "/"
        self.apps[script_name] = app
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
        
        while path:
            if path in self.apps:
                return path
            
            # Move one node up the tree and try again.
            if path == "/":
                break
            path = path[:path.rfind("/")] or "/"
        
        return None
    
    def url(self, path, script_name=None):
        """Return 'path', prefixed with script_name.
        
        If script_name is None, cherrypy.request.path will be used
        to find a script_name.
        """
        
        if script_name is None:
            script_name = self.script_name()
            if script_name is None:
                return path
        
        from cherrypy.lib import httptools
        return httptools.urljoin(script_name, path)

