"""A few utility classes/functions used by CherryPy."""

import cherrypy


def notfound():
    raise cherrypy.NotFound()

class Dispatcher(object):
    
    def __call__(self, path_info):
        """Set handler and config for the current request."""
        request = cherrypy.request
        func, vpath = self.find_handler(path_info)
        
        # Decode any leftover %2F in the virtual_path atoms.
        vpath = [x.replace("%2F", "/") for x in vpath]
        
        if func:
            def handler():
                cherrypy.response.body = func(*vpath, **request.params)
            request.handler = handler
        else:
            request.handler = notfound
    
    def find_handler(self, path):
        """Find the appropriate page handler for the given path."""
        request = cherrypy.request
        app = request.app
        root = app.root
        
        # Get config for the root object/path.
        curpath = ""
        nodeconf = getattr(root, "_cp_config", {}).copy()
        nodeconf.update(app.conf.get("/", {}))
        object_trail = [('root', root, nodeconf, curpath)]
        
        node = root
        names = [x for x in path.strip('/').split('/') if x] + ['index']
        for name in names:
            # map to legal Python identifiers (replace '.' with '_')
            objname = name.replace('.', '_')
            
            nodeconf = {}
            node = getattr(node, objname, None)
            if node is not None:
                # Get _cp_config attached to this node.
                nodeconf = getattr(node, "_cp_config", {}).copy()
            
            # Mix in values from app.conf for this path.
            curpath = "/".join((curpath, name))
            nodeconf.update(app.conf.get(curpath, {}))
            
            # Resolve "environment" entries. This must be done node-by-node
            # so that a child's "environment" can override concrete settings
            # of a parent. However, concrete settings in this node will
            # override "environment" settings in the same node.
            env = nodeconf.get("environment")
            if env:
                for k, v in cherrypy.config.environments[env].iteritems():
                    if k not in nodeconf:
                        nodeconf[k] = v
            
            object_trail.append((objname, node, nodeconf, curpath))
        
        def set_conf():
            """Set cherrypy.request.config."""
            base = cherrypy.config.globalconf.copy()
            if 'tools.staticdir.dir' in base:
                base['tools.staticdir.section'] = "global"
            for name, obj, conf, curpath in object_trail:
                base.update(conf)
                if 'tools.staticdir.dir' in conf:
                    base['tools.staticdir.section'] = curpath
            request.config = base
        
        # Try successive objects (reverse order)
        for i in xrange(len(object_trail) - 1, -1, -1):
            
            name, candidate, nodeconf, curpath = object_trail[i]
            
            # Try a "default" method on the current leaf.
            defhandler = getattr(candidate, "default", None)
            if callable(defhandler) and getattr(defhandler, 'exposed', False):
                # Insert any extra _cp_config from the default handler.
                conf = getattr(defhandler, "_cp_config", {})
                object_trail.insert(i+1, ("default", defhandler, conf, curpath))
                set_conf()
                return defhandler, names[i:-1]
            
            # Uncomment the next line to restrict positional params to "default".
            # if i < len(object_trail) - 2: continue
            
            # Try the current leaf.
            if callable(candidate) and getattr(candidate, 'exposed', False):
                set_conf()
                if i == len(object_trail) - 1:
                    # We found the extra ".index". Check if the original path
                    # had a trailing slash (otherwise, do a redirect).
                    if not path.endswith('/'):
                        atoms = request.browser_url.split("?", 1)
                        newUrl = atoms.pop(0) + '/'
                        if atoms:
                            newUrl += "?" + atoms[0]
                        raise cherrypy.HTTPRedirect(newUrl)
                return candidate, names[i:-1]
        
        # We didn't find anything
        set_conf()
        return None, []

dispatch = Dispatcher()
