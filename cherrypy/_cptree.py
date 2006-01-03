
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
        self.mount_points = {}
    
    def mount(self, app_root, baseurl="/", conf=None):
        """Mount the given app_root at the given baseurl (relative to root)."""
        import cherrypy
        
        point = baseurl.lstrip("/")
        if point:
            node = cherrypy.root
            if node is None:
                node = Root()
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
            if isinstance(conf, dict):
                cherrypy.config.update(updateMap=conf, baseurl=baseurl)
            else:
                cherrypy.config.update(file=conf, baseurl=baseurl)

