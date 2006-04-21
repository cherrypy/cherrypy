import os
import re
import urllib

import cherrypy
from cherrypy.lib import static


def get(root, dir, match="", content_types=None, index=""):
    if not os.path.isabs(dir):
        msg = "static directory requires an absolute path."
        raise cherrypy.WrongConfigValue(msg)
    
    request = cherrypy.request
    path = request.object_path
    
    if match and not re.search(match, path):
        return False
    
    if root == 'global':
        root = "/"
    root = root.rstrip(r"\/")
    
    branch = urllib.unquote(path[len(root) + 1:].lstrip(r"\/"))
    
    # If branch is "", file will end in a slash
    file = os.path.join(dir, branch)
    
    # There's a chance that the branch pulled from the URL might
    # have ".." or similar uplevel attacks in it. Check that the final
    # file is a child of dir.
    if not os.path.normpath(file).startswith(os.path.normpath(dir)):
        raise cherrypy.HTTPError(403) # Forbidden
    
    def attempt(fname):
        # you can set the content types for a
        # complete directory per extension
        content_type = None
        if content_types:
            r, ext = os.path.splitext(fname)
            content_type = content_types.get(ext[1:], None)
        serve_file(fname, contentType=content_type)
    
    try:
        attempt(file)
        return True
    except cherrypy.NotFound:
        # If we didn't find the static file, continue handling the
        # request. We might find a dynamic handler instead.
        
        # But first check for an index file if a folder was requested.
        if index and file[-1] in (r"\/"):
            try:
                attempt(os.path.join(file, index))
                return True
            except cherrypy.NotFound:
                pass
    return False

def wrap(f, section, dir):
    """Static directory decorator."""
    def _get(*args, **kwargs):
        if not get(section, dir):
            f(*args, **kwargs)
    return _get

def setup(conf):
    """Hook the dir tool into cherrypy.request using the given conf."""
    cherrypy.request.hooks.attach_main(get, conf)
