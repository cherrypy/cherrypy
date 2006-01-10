"""A few utility classes/functions used by CherryPy."""

import cgi
import datetime
import sys
import traceback

import cherrypy
from cherrypy.lib import httptools

def get_object_trail(objectpath=None):
    """
    List of (name, object) pairs, from cherrypy.root to the current object.
    
    If any named objects are unreachable, (name, None) pairs are used.
    """
    
    if objectpath is None:
        try:
            objectpath = cherrypy.request.object_path
        except AttributeError:
            pass
    
    if objectpath is not None:
        objectpath = objectpath.strip('/')
    
    # Convert the objectpath into a list of names
    if not objectpath:
        nameList = []
    else:
        nameList = objectpath.split('/')
    
    if nameList == ['global']:
        # Special-case a Request-URI of * to allow for our default handler.
        root = getattr(cherrypy, 'root', None)
        if root is None:
            return [('root', None), ('global_', None), ('index', None)]
        gh = getattr(root, 'global_', _cpGlobalHandler)
        return [('root', cherrypy.root), ('global_', gh), ('index', None)]
    
    nameList = ['root'] + nameList + ['index']
    
    # Convert the list of names into a list of objects
    node = cherrypy
    objectTrail = []
    for name in nameList:
        # maps virtual names to Python identifiers (replaces '.' with '_')
        objname = name.replace('.', '_')
        node = getattr(node, objname, None)
        if node is None:
            objectTrail.append((name, node))
        else:
            objectTrail.append((objname, node))
    
    return objectTrail

def get_special_attribute(name, old_name = None):
    """Return the special attribute. A special attribute is one that
    applies to all of the children from where it is defined, such as
    _cp_filters."""
    
    # First, we look in the right-most object to see if this special
    # attribute is implemented. If not, then we try the previous object,
    # and so on until we reach cherrypy.root, or a mount point.
    # If it's still not there, we use the implementation from this module.
    mounted_app_roots = cherrypy.tree.mount_points.values()
    objectList = get_object_trail()
    objectList.reverse()
    for objname, obj in objectList:
        if old_name and hasattr(obj, old_name):
            return getattr(obj, old_name)
        elif hasattr(obj, name):
            return getattr(obj, name)
        if obj in mounted_app_roots:
            break
    
    try:
        if old_name:
            return globals()[old_name]
        else:
            return globals()[name]
    except KeyError:
        if old_name:
            return get_special_attribute(name)
        msg = "Special attribute %s could not be found" % repr(name)
        raise cherrypy.HTTPError(500, msg)

def _cpGlobalHandler():
    """Default handler for a Request-URI of '*'."""
    response = cherrypy.response
    response.headers['Content-Type'] = 'text/plain'
    
    # OPTIONS is defined in HTTP 1.1 and greater
    request = cherrypy.request
    if request.method == 'OPTIONS' and request.version >= 1.1:
        response.headers['Allow'] = 'HEAD, GET, POST, PUT, OPTIONS'
    else:
        response.headers['Allow'] = 'HEAD, GET, POST'
    return ""
_cpGlobalHandler.exposed = True

def logtime():
    now = datetime.datetime.now()
    month = httptools.monthname[now.month][:3].capitalize()
    return '%02d/%s/%04d:%02d:%02d:%02d' % (
        now.day, month, now.year, now.hour, now.minute, now.second)

def _cp_log_access():
    """ Default method for logging access """
    
    tmpl = '%(h)s %(l)s %(u)s [%(t)s] "%(r)s" %(s)s %(b)s'
    s = tmpl % {'h': cherrypy.request.remoteHost,
                'l': '-',
                'u': getattr(cherrypy.request, "login", None) or "-",
                't': logtime(),
                'r': cherrypy.request.requestLine,
                's': cherrypy.response.status.split(" ", 1)[0],
                'b': cherrypy.response.headers.get('Content-Length', '') or "-",
                }
    
    if cherrypy.config.get('server.log_to_screen', True):
        print s
    
    fname = cherrypy.config.get('server.log_access_file', '')
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
    
    if cherrypy.config.get('server.log_to_screen', True):
        print s
    
    fname = cherrypy.config.get('server.log_file', '')
    #logdir = os.path.dirname(fname)
    #if logdir and not os.path.exists(logdir):
    #    os.makedirs(logdir)
    if fname:
        f = open(fname, 'ab')
        f.write(s + '\n')
        f.close()


_HTTPErrorTemplate = '''<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html>
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8"></meta>
    <title>%(status)s</title>
    <style type="text/css">
    #powered_by {
        margin-top: 20px;
        border-top: 2px solid black;
        font-style: italic;
    }

    #traceback {
        color: red;
    }
    </style>
</head>
    <body>
        <h2>%(status)s</h2>
        <p>%(message)s</p>
        <pre id="traceback">%(traceback)s</pre>
    <div id="powered_by">
    <span>Powered by <a href="http://www.cherrypy.org">CherryPy %(version)s</a></span>
    </div>
    </body>
</html>
'''

def getErrorPage(status, **kwargs):
    """Return an HTML page, containing a pretty error response.
    
    status should be an int or a str.
    kwargs will be interpolated into the page template.
    """
    
    try:
        code, reason, message = httptools.validStatus(status)
    except ValueError, x:
        raise cherrypy.HTTPError(500, x.args[0])
    
    # We can't use setdefault here, because some
    # callers send None for kwarg values.
    if kwargs.get('status') is None:
        kwargs['status'] = "%s %s" % (code, reason)
    if kwargs.get('message') is None:
        kwargs['message'] = message
    if kwargs.get('traceback') is None:
        kwargs['traceback'] = ''
    if kwargs.get('version') is None:
        kwargs['version'] = cherrypy.__version__
    for k, v in kwargs.iteritems():
        if v is None:
            kwargs[k] = ""
        else:
            kwargs[k] = cgi.escape(kwargs[k])
    
    template = _HTTPErrorTemplate
    error_page_file = cherrypy.config.get('error_page.%s' % code, '')
    if error_page_file:
        try:
            template = file(error_page_file, 'rb').read()
        except:
            m = kwargs['message']
            if m:
                m += "<br />"
            m += ("In addition, the custom error page "
                  "failed:\n<br />%s" % (sys.exc_info()[1]))
            kwargs['message'] = m
    
    return template % kwargs


def _cp_on_http_error(status, message):
    """ Default _cp_on_http_error method.
    
    status should be an int.
    """
    tb = formatExc()
    logmsg = ""
    
    if cherrypy.config.get('server.log_tracebacks', True):
        logmsg = tb
    if cherrypy.config.get('server.log_request_headers', True):
        h = ["  %s: %s" % (k, v) for k, v in cherrypy.request.header_list]
        logmsg += 'Request Headers:\n' + '\n'.join(h)
    if logmsg:
        cherrypy.log(logmsg, "HTTP")
    
    if not cherrypy.config.get('server.show_tracebacks', False):
        tb = None
    
    response = cherrypy.response
    
    # Remove headers which applied to the original content,
    # but do not apply to the error page.
    for key in ["Accept-Ranges", "Age", "ETag", "Location", "Retry-After",
                "Vary", "Content-Encoding", "Content-Length", "Expires",
                "Content-Location", "Content-MD5", "Last-Modified"]:
        if response.headers.has_key(key):
            del response.headers[key]
    
    if status != 416:
        # A server sending a response with status code 416 (Requested
        # range not satisfiable) SHOULD include a Content-Range field
        # with a byte-range- resp-spec of "*". The instance-length
        # specifies the current length of the selected resource.
        # A response with status code 206 (Partial Content) MUST NOT
        # include a Content-Range field with a byte-range- resp-spec of "*".
        if response.headers.has_key("Content-Range"):
            del response.headers["Content-Range"]
    
    # In all cases, finalize will be called after this method,
    # so don't bother cleaning up response values here.
    response.status = status
    content = getErrorPage(status, traceback=tb, message=message)
    response.body = content
    response.headers['Content-Length'] = len(content)
    response.headers['Content-Type'] = "text/html"
    
    be_ie_unfriendly(status)


_ie_friendly_error_sizes = {
    400: 512, 403: 256, 404: 512, 405: 256,
    406: 512, 408: 512, 409: 512, 410: 256,
    500: 512, 501: 512, 505: 512,
    }


def be_ie_unfriendly(status):
    
    response = cherrypy.response
    
    # For some statuses, Internet Explorer 5+ shows "friendly error
    # messages" instead of our response.body if the body is smaller
    # than a given size. Fix this by returning a body over that size
    # (by adding whitespace).
    # See http://support.microsoft.com/kb/q218155/
    s = _ie_friendly_error_sizes.get(status, 0)
    if s:
        s += 1
        # Since we are issuing an HTTP error status, we assume that
        # the entity is short, and we should just collapse it.
        content = response.collapse_body()
        l = len(content)
        if l and l < s:
            # IN ADDITION: the response must be written to IE
            # in one chunk or it will still get replaced! Bah.
            content = content + (" " * (s - l))
        response.body = content
        response.headers['Content-Length'] = len(content)

def lower_to_camel(s):
    """Turns lowercase_with_underscore into camelCase."""
    sp = s.split('_')
    new_sp = []
    for i, s in enumerate(sp):
        if i != 0:
            s = s[0].upper() + s[1:]
        new_sp.append(s)
    return ''.join(new_sp)

def formatExc(exc=None):
    """formatExc(exc=None) -> exc (or sys.exc_info if None), formatted."""
    if exc is None:
        exc = sys.exc_info()
    
    if exc == (None, None, None):
        return ""
    return "".join(traceback.format_exception(*exc))

def bareError(extrabody=None):
    """Produce status, headers, body for a critical error.
    
    Returns a triple without calling any other questionable functions,
    so it should be as error-free as possible. Call it from an HTTP server
    if you get errors after Request() is done.
    
    If extrabody is None, a friendly but rather unhelpful error message
    is set in the body. If extrabody is a string, it will be appended
    as-is to the body.
    """
    
    # The whole point of this function is to be a last line-of-defense
    # in handling errors. That is, it must not raise any errors itself;
    # it cannot be allowed to fail. Therefore, don't add to it!
    # In particular, don't call any other CP functions.
    
    body = "Unrecoverable error in the server."
    if extrabody is not None:
        body += "\n" + extrabody
    
    return ("500 Internal Server Error",
            [('Content-Type', 'text/plain'),
             ('Content-Length', str(len(body)))],
            [body])

def _cp_on_error():
    """ Default _cp_on_error method """
    # Allow logging of only *unexpected* HTTPError's.
    if (not cherrypy.config.get('server.log_tracebacks', True)
        and cherrypy.config.get('server.log_unhandled_tracebacks', True)):
        cherrypy.log(traceback=True)
    
    cherrypy.HTTPError(500).set_response()

def headers(headers):
    """ Provides a simple way to add specific headers to page handler
    Any previously set headers provided in the list of tuples will be changed
    
    headers - a list of tuple : (header_name, header_value)
    """
    def wrapper(func):
        def inner(*args):
            for item in headers:
                headername = item[0]
                headervalue = item[1]
                cherrypy.response.headerMap[headername] = headervalue
            return func(*args)
        return inner
    return wrapper

_cp_filters = []

