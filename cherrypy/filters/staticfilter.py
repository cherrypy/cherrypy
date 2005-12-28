import os
import urllib

import cherrypy
from cherrypy.lib import cptools
from cherrypy.filters.basefilter import BaseFilter


class StaticFilter(BaseFilter):
    """Filter that handles static content."""
    
    def before_main(self):
        config = cherrypy.config
        if not config.get('static_filter.on', False):
            return
        
        request = cherrypy.request
        path = request.object_path
        
        regex = config.get('static_filter.match', '')
        if regex:
            import re
            if not re.search(regex, path):
                return
        
        filename = config.get('static_filter.file')
        if not filename:
            staticDir = config.get('static_filter.dir')
            section = config.get('static_filter.dir', return_section=True)
            if section == 'global':
                section = "/"
            section = section.rstrip(r"\/")
            extraPath = path[len(section) + 1:]
            extraPath = extraPath.lstrip(r"\/")
            extraPath = urllib.unquote(extraPath)
            filename = os.path.join(staticDir, extraPath)
        
        # If filename is relative, make absolute using "root".
        if not os.path.isabs(filename):
            root = config.get('static_filter.root', '').rstrip(r"\/")
            if root:
                filename = os.path.join(root, filename)

        try:        
            cptools.serveFile(filename)
            request.execute_main = False
        except cherrypy.NotFound:
            # if we didn't find the static file, continue
            # handling the request. we might find a dynamic
            # handler instead.
            pass
        
