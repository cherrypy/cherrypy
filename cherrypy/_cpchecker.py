import os
import warnings

import cherrypy


class Checker(object):
    
    global_config_contained_paths = False
    
    def checkall(self):
        oldformatwarning = warnings.formatwarning
        warnings.formatwarning = self.formatwarning
        try:
            for name in dir(self):
                if name.startswith("check_"):
                    method = getattr(self, name)
                    method()
        finally:
            warnings.formatwarning = oldformatwarning
    
    def formatwarning(self, message, category, filename, lineno):
        """Function to format a warning."""
        return "CherryPy Checker:\n%s\n\n" % message
    
    def check_skipped_app_config(self):
        for sn, app in cherrypy.tree.apps.iteritems():
            if not app.config:
                msg = "The Application mounted at %r has an empty config." % sn
                if self.global_config_contained_paths:
                    msg += (" It looks like the config you passed to "
                            "cherrypy.config.update() contains application-"
                            "specific sections. You must explicitly pass "
                            "application config via "
                            "cherrypy.tree.mount(..., config=app_config)")
                warnings.warn(msg)
                return
    
    def check_static_paths(self):
        # Use the dummy Request object in the main thread.
        request = cherrypy.request
        for sn, app in cherrypy.tree.apps.iteritems():
            request.app = app
            for section in app.config:
                # get_resource will populate request.config
                request.get_resource(section + "/dummy.html")
                conf = request.config.get
                
                if conf("tools.staticdir.on", False):
                    msg = ""
                    root = conf("tools.staticdir.root")
                    dir = conf("tools.staticdir.dir")
                    if dir is None:
                        msg = "tools.staticdir.dir is not set."
                    else:
                        fulldir = ""
                        if os.path.isabs(dir):
                            fulldir = dir
                            if root:
                                msg = "dir is an absolute path, even though a root is provided."
                                testdir = os.path.join(root, dir[1:])
                                if os.path.exists(testdir):
                                    msg += ("\nIf you meant to serve the filesystem folder at %r, "
                                            "remove the leading slash from dir." % testdir)
                        else:
                            if not root:
                                msg = "dir is a relative path and no root provided."
                            else:
                                fulldir = os.path.join(root, dir)
                                if not os.path.isabs(fulldir):
                                    msg = "%r is not an absolute path." % fulldir
                        
                        if fulldir and not os.path.exists(fulldir):
                            if msg:
                                msg += "\n"
                            msg += "%r (root + dir) is not an existing filesystem path." % fulldir
                    
                    if msg:
                        warnings.warn("%s\nsection: [%s]\nroot: %r\ndir: %r"
                                      % (msg, section, root, dir))

