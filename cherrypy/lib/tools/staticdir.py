import os
import re

import cherrypy
from cherrypy.lib.compat import unquote
from cherrypy.lib.static import attempt


def staticdir(section, dir, root="", match="", content_types=None, index="",
              debug=False):
    """Serve a static resource from the given (root +) dir.

    match
        If given, request.path_info will be searched for the given
        regular expression before attempting to serve static content.

    content_types
        If given, it should be a Python dictionary of
        {file-extension: content-type} pairs, where 'file-extension' is
        a string (e.g. "gif") and 'content-type' is the value to write
        out in the Content-Type response header (e.g. "image/gif").

    index
        If provided, it should be the (relative) name of a file to
        serve for directory requests. For example, if the dir argument is
        '/home/me', the Request-URI is 'myapp', and the index arg is
        'index.html', the file '/home/me/myapp/index.html' will be sought.
    """
    request = cherrypy.serving.request
    if request.method not in ('GET', 'HEAD'):
        if debug:
            cherrypy.log('request.method not GET or HEAD', 'TOOLS.STATICDIR')
        return False

    if match and not re.search(match, request.path_info):
        if debug:
            cherrypy.log('request.path_info %r does not match pattern %r' %
                         (request.path_info, match), 'TOOLS.STATICDIR')
        return False

    # Allow the use of '~' to refer to a user's home directory.
    dir = os.path.expanduser(dir)

    # If dir is relative, make absolute using "root".
    if not os.path.isabs(dir):
        if not root:
            msg = "Static dir requires an absolute dir (or root)."
            if debug:
                cherrypy.log(msg, 'TOOLS.STATICDIR')
            raise ValueError(msg)
        dir = os.path.join(root, dir)

    # Determine where we are in the object tree relative to 'section'
    # (where the static tool was defined).
    if section == 'global':
        section = "/"
    section = section.rstrip(r"\/")
    branch = request.path_info[len(section) + 1:]
    branch = unquote(branch.lstrip(r"\/"))

    # If branch is "", filename will end in a slash
    filename = os.path.join(dir, branch)
    if debug:
        cherrypy.log('Checking file %r to fulfill %r' %
                     (filename, request.path_info), 'TOOLS.STATICDIR')

    # There's a chance that the branch pulled from the URL might
    # have ".." or similar uplevel attacks in it. Check that the final
    # filename is a child of dir.
    if not os.path.normpath(filename).startswith(os.path.normpath(dir)):
        raise cherrypy.HTTPError(403)  # Forbidden

    handled = attempt(filename, content_types)
    if not handled:
        # Check for an index file if a folder was requested.
        if index:
            handled = attempt(os.path.join(filename, index), content_types)
            if handled:
                request.is_index = filename[-1] in r"\/"
    return handled
