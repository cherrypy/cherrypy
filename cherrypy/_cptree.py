
class Application:
    
    def __init__(self, root, conf):
        self.root = root
        self.conf = conf


class Tree:
    """A registry of mounted applications at diverse points."""
    
    def __init__(self):
        self.apps = {}
    
    def mount(self, root, script_name=None, conf=None):
        """Mount the given application root object at the given script_name."""
        import cherrypy
        
        if conf and not isinstance(conf, dict):
            conf = cherrypy.config.dict_from_config_file(conf)
        elif conf is None:
            conf = {}
        
        if script_name is None:
            script_name = "/"
            if conf:
                conf_pt = conf.get("global", {}).get("script_name")
                if conf_pt:
                    script_name = conf_pt
        
        self.apps[script_name] = Application(root, conf)
    
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

