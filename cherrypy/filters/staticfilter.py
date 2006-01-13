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
        
        root = config.get('static_filter.root', '').rstrip(r"\/")
        filename = config.get('static_filter.file')
        if filename:
            staticDir = None
        else:
            staticDir = config.get('static_filter.dir')
            if not staticDir:
                msg = ("StaticFilter requires either static_filter.file "
                       "or static_filter.dir (%s)" % request.path)
                raise cherrypy.WrongConfigValue(msg)
            section = config.get('static_filter.dir', return_section=True)
            if section == 'global':
                section = "/"
            section = section.rstrip(r"\/")
            extraPath = path[len(section) + 1:]
            extraPath = extraPath.lstrip(r"\/")
            extraPath = urllib.unquote(extraPath)
            # If extraPath is "", filename will end in a slash
            filename = os.path.join(staticDir, extraPath)
        
        # If filename is relative, make absolute using "root".
        # Note that, if "root" isn't defined, we still may send
        # a relative path to serveFile.
        if not os.path.isabs(filename):
            if not root:
                msg = ("StaticFilter requires an absolute final path. "
                       "Make static_filter.dir, .file, or .root absolute.")
                raise cherrypy.WrongConfigValue(msg)
            filename = os.path.join(root, filename)
        
        # If we used static_filter.dir, then there's a chance that the
        # extraPath pulled from the URL might have ".." or similar uplevel
        # attacks in it. Check that the final file is a child of staticDir.
        # Note that we do not check static_filter.file--that can point
        # anywhere (since it does not use the request URL).
        if staticDir:
            if not os.path.isabs(staticDir):
                staticDir = os.path.join(root, staticDir)
            if not os.path.normpath(filename).startswith(os.path.normpath(staticDir)):
                raise cherrypy.HTTPError(403) # Forbidden
            
        try:
            # you can set the content types for a complete directory per extension
            content_types = config.get('static_filter.content_types', None)
            content_type = None
            if content_types:
                root, ext = os.path.splitext(filename)
                content_type = content_types.get(ext[1:], None)
            cptools.serveFile(filename, contentType=content_type)
            request.execute_main = False
        except cherrypy.NotFound:
            # If we didn't find the static file, continue handling the
            # request. We might find a dynamic handler instead.
            
            # But first check for an index file if a folder was requested.
            if filename[-1:] in ("/", "\\"):
                idx = config.get('static_filter.index', '')
                if idx:
                    try:
                        cptools.serveFile(os.path.join(filename, idx))
                        request.execute_main = False
                    except cherrypy.NotFound:
                        pass
