import os
import urllib

import cherrypy
from cherrypy.lib import cptools
from cherrypy.filters.basefilter import BaseFilter


class StaticFilter(BaseFilter):
    """Filter that handles static content."""
    
    def beforeMain(self):
        config = cherrypy.config
        if not config.get('staticFilter.on', False):
            return
        
        request = cherrypy.request
        path = request.objectPath
        
        regex = config.get('staticFilter.match', '')
        if regex:
            import re
            if not re.search(regex, path):
                return
        
        filename = config.get('staticFilter.file')
        if not filename:
            staticDir = config.get('staticFilter.dir')
            section = config.get('staticFilter.dir', returnSection=True)
            if section == 'global':
                section = "/"
            section = section.rstrip(r"\/")
            extraPath = path[len(section) + 1:]
            extraPath = extraPath.lstrip(r"\/")
            extraPath = urllib.unquote(extraPath)
            filename = os.path.join(staticDir, extraPath)
        
        # If filename is relative, make absolute using "root".
        if not os.path.isabs(filename):
            root = config.get('staticFilter.root', '').rstrip(r"\/")
            if root:
                filename = os.path.join(root, filename)
        
        cptools.serveFile(filename)
        request.executeMain = False

