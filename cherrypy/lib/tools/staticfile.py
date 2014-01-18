import os
import re

import cherrypy
from cherrypy.lib.static import attempt


def staticfile(filename, root=None, match="", content_types=None, debug=False):
    """Serve a static resource from the given (root +) filename.

    match
        If given, request.path_info will be searched for the given
        regular expression before attempting to serve static content.

    content_types
        If given, it should be a Python dictionary of
        {file-extension: content-type} pairs, where 'file-extension' is
        a string (e.g. "gif") and 'content-type' is the value to write
        out in the Content-Type response header (e.g. "image/gif").

    """
    request = cherrypy.serving.request
    if request.method not in ('GET', 'HEAD'):
        if debug:
            cherrypy.log('request.method not GET or HEAD', 'TOOLS.STATICFILE')
        return False

    if match and not re.search(match, request.path_info):
        if debug:
            cherrypy.log('request.path_info %r does not match pattern %r' %
                         (request.path_info, match), 'TOOLS.STATICFILE')
        return False

    # If filename is relative, make absolute using "root".
    if not os.path.isabs(filename):
        if not root:
            msg = "Static tool requires an absolute filename (got '%s')." % (
                filename,)
            if debug:
                cherrypy.log(msg, 'TOOLS.STATICFILE')
            raise ValueError(msg)
        filename = os.path.join(root, filename)

    return attempt(filename, content_types, debug=debug)
