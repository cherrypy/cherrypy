
from cherrypy import config


class Application:
    
    def __init__(self, root, script_name="", conf=None):
        self.root = root
        self.script_name = script_name
        self.conf = {}
        if conf:
            self.merge(conf)
    
    def merge(self, conf):
        config.merge(self.conf, conf)


class Tree:
    """A registry of mounted applications at diverse points."""
    
    def __init__(self):
        self.apps = {}
    
    def mount(self, root, script_name="", conf=None):
        """Mount a new app from a root object, script_name, and conf."""
        if script_name == "/":
            script_name = ""
        app = Application(root, script_name, conf)
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
        
        from cherrypy.lib import httptools
        return httptools.urljoin(script_name, path)

