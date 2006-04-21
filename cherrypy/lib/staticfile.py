import os
import re

import cherrypy
from cherrypy.lib import static


def get(filename, match="", content_types=None):
    if not os.path.isabs(filename):
        msg = "static file requires an absolute path."
        raise cherrypy.WrongConfigValue(msg)
    
    request = cherrypy.request
    path = request.object_path
    
    if match and not re.search(match, path):
        return False
    
    try:
        # you can set the content types for a complete directory per extension
        content_type = None
        if content_types:
            root, ext = os.path.splitext(filename)
            content_type = content_types.get(ext[1:], None)
        serve_file(filename, contentType=content_type)
        return True
    except cherrypy.NotFound:
        # If we didn't find the static file, continue handling the
        # request. We might find a dynamic handler instead.
        return False


def wrap(f, filename):
    """Static file decorator."""
    def _get(*args, **kwargs):
        if not get(filename):
            f(*args, **kwargs)
    return _get

def setup(conf):
    """Hook the file tool into cherrypy.request using the given conf."""
    cherrypy.request.hooks.attach_main(get, conf)

