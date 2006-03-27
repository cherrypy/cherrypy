
class Root:
    pass

class Branch:
    pass


class Tree:
    """A scaffold for cherrypy.root.
    
    This class works together with cherrypy.root, providing helper methods
    for mounting applications at diverse points. "Trellis" would be a more
    accurate name (but too hard to remember, and perhaps in CP 3.0 this
    class will become cherrypy.root).
    """
    
    def __init__(self):
        self._mount_points = {}
    
    def _get_mount_points(self):
        m = self._mount_points
        if "/" not in m:
            import cherrypy
            if cherrypy.root is not None and not isinstance(cherrypy.root, Root):
                m["/"] = cherrypy.root
        return m
    def _set_mount_points(self, newvalue):
        self._mount_points = newvalue
    mount_points = property(_get_mount_points, _set_mount_points)
    
    def mount(self, app_root, baseurl=None, conf=None):
        """Mount the given app_root at the given baseurl (relative to root)."""
        import cherrypy
        
        if conf and not isinstance(conf, dict):
            conf = cherrypy.config.dict_from_config_file(conf)
        
        if baseurl is None:
            baseurl = "/"
            if conf:
                conf_pt = conf.get("global", {}).get("mount_point")
                if conf_pt:
                    baseurl = conf_pt
        
        point = baseurl.lstrip("/")
        if point:
            node = cherrypy.root
            if node is None:
                node = cherrypy.root = Root()
            atoms = point.split("/")
            tail = atoms.pop()
            for atom in atoms:
                if not hasattr(node, atom):
                    setattr(node, atom, Branch())
                node = getattr(node, atom)
            if hasattr(node, tail):
                raise ValueError("The url '%s' is already mounted." % baseurl)
        else:
            # Mount the app_root at cherrypy.root.
            if cherrypy.root is not None:
                raise ValueError("The url '%s' is already mounted." % baseurl)
            node = cherrypy
            tail = "root"
        
        setattr(node, tail, app_root)
        self.mount_points[baseurl] = app_root
        
        if conf is not None:
            cherrypy.config.update(updateMap=conf, baseurl=baseurl)
    
    def mount_point(self, path=None):
        """The 'root path' of the app which governs the given path, or None.
        
        If path is None, cherrypy.request.object_path is used.
        """
        
        if path is None:
            try:
                import cherrypy
                path = cherrypy.request.object_path
            except AttributeError:
                return None
        
        while path:
            if path in self.mount_points:
                return path
            
            # Move one node up the tree and try again.
            if path == "/":
                break
            path = path[:path.rfind("/")] or "/"
        
        return None
    
    def url(self, path, mount_point=None):
        """Return 'path', prefixed with mount_point.
        
        If mount_point is None, cherrypy.request.object_path will be used
        to find a mount point.
        """
        
        if mount_point is None:
            mount_point = self.mount_point()
            if mount_point is None:
                return path
        
        from cherrypy.lib import httptools
        return httptools.urljoin(mount_point, path)

