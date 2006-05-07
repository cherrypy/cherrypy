"""A few utility classes/functions used by CherryPy."""

import cgi
import datetime
import sys
import traceback

import cherrypy
from cherrypy.lib import httptools


def get_object_trail(path=None, root=None):
    """List of (name, object) pairs, from root (app.root) down path.
    
    If any named objects are unreachable, (name, None) pairs are used.
    """
    
    if path is None:
        try:
            path = cherrypy.request.path_info
        except AttributeError:
            pass
    
    if path is not None:
        path = path.strip('/')
    
    # Convert the path into a list of names
    if not path:
        nameList = []
    else:
        nameList = path.split('/')
    
    if root is None:
        try:
            root = cherrypy.request.app.root
        except AttributeError:
            return [('root', None), ('index', None)]
    
    nameList.append('index')
    
    # Convert the list of names into a list of objects
    node = root
    object_trail = [('root', root)]
    for name in nameList:
        # maps virtual names to Python identifiers (replaces '.' with '_')
        objname = name.replace('.', '_')
        node = getattr(node, objname, None)
        if node is None:
            object_trail.append((name, node))
        else:
            object_trail.append((objname, node))
    
    return object_trail

def dispatch(path):
    """Find and run the appropriate page handler."""
    request = cherrypy.request
    handler, opath, vpath = find_handler(path)
    
    # Remove "root" from opath and join it to get found_object_path
    # There are no consumers of this info right now, so this block
    # may disappear soon.
    if opath and opath[0] == "root":
        opath.pop(0)
    request.found_object_path = '/' + '/'.join(opath)
    
    # Decode any leftover %2F in the virtual_path atoms.
    vpath = [x.replace("%2F", "/") for x in vpath]
    cherrypy.response.body = handler(*vpath, **request.params)

def find_handler(path):
    """Find the appropriate page handler for the given path."""
    object_trail = get_object_trail(path)
    names = [name for name, candidate in object_trail]
    
    # Try successive objects (reverse order)
    for i in xrange(len(object_trail) - 1, -1, -1):
        
        name, candidate = object_trail[i]
        
        # Try a "default" method on the current leaf.
        defhandler = getattr(candidate, "default", None)
        if callable(defhandler) and getattr(defhandler, 'exposed', False):
            return defhandler, names[:i+1] + ["default"], names[i+1:-1]
        
        # Uncomment the next line to restrict positional params to "default".
        # if i < len(object_trail) - 2: continue
        
        # Try the current leaf.
        if callable(candidate) and getattr(candidate, 'exposed', False):
            if i == len(object_trail) - 1:
                # We found the extra ".index". Check if the original path
                # had a trailing slash (otherwise, do a redirect).
                if not path.endswith('/'):
                    atoms = cherrypy.request.browser_url.split("?", 1)
                    newUrl = atoms.pop(0) + '/'
                    if atoms:
                        newUrl += "?" + atoms[0]
                    raise cherrypy.HTTPRedirect(newUrl)
            return candidate, names[:i+1], names[i+1:-1]
    
    # We didn't find anything
    raise cherrypy.NotFound(path)


def get_special_attribute(name):
    """Return the special attribute. A special attribute is one that
    applies to all of the children from where it is defined."""
    
    # First, we look in the right-most object to see if this special
    # attribute is implemented. If not, then we try the previous object,
    # and so on until we reach app.root (a mount point).
    # If it's still not there, we use the implementation from this module.
    objectList = get_object_trail()
    objectList.reverse()
    for objname, obj in objectList:
        if hasattr(obj, name):
            return getattr(obj, name)
    
    try:
        return globals()[name]
    except KeyError:
        msg = "Special attribute %s could not be found" % repr(name)
        raise cherrypy.HTTPError(500, msg)

def logtime():
    now = datetime.datetime.now()
    month = httptools.monthname[now.month][:3].capitalize()
    return '%02d/%s/%04d:%02d:%02d:%02d' % (
        now.day, month, now.year, now.hour, now.minute, now.second)

def log_access():
    """Default method for logging access"""
    request = cherrypy.request
    
    tmpl = '%(h)s %(l)s %(u)s [%(t)s] "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'
    s = tmpl % {'h': request.remote_host,
                'l': '-',
                'u': getattr(request, "login", None) or "-",
                't': logtime(),
                'r': request.request_line,
                's': cherrypy.response.status.split(" ", 1)[0],
                'b': cherrypy.response.headers.get('Content-Length', '') or "-",
                'f': request.headers.get('referer', ''),
                'a': request.headers.get('user-agent', ''),
                }
    
    if cherrypy.config.get('log_to_screen', True):
        print s
    
    fname = cherrypy.config.get('log_access_file', '')
    if fname:
        f = open(fname, 'ab')
        f.write(s + '\n')
        f.close()

_log_severity_levels = {0: "INFO", 1: "WARNING", 2: "ERROR"}

def _cp_log_message(msg, context = '', severity = 0):
    """Default method for logging messages (error log).
    
    This is not just for errors! Applications may call this at any time to
    log application-specific information.
    """
    
    level = _log_severity_levels.get(severity, "UNKNOWN")
    
    s = ' '.join((logtime(), context, level, msg))
    
    if cherrypy.config.get('log_to_screen', True):
        print s
    
    fname = cherrypy.config.get('log_file', '')
    #logdir = os.path.dirname(fname)
    #if logdir and not os.path.exists(logdir):
    #    os.makedirs(logdir)
    if fname:
        f = open(fname, 'ab')
        f.write(s + '\n')
        f.close()

