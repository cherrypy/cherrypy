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
            objectpath = cherrypy.request.objectPath
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

def getSpecialAttribute(name):
    """Return the special attribute. A special attribute is one that
    applies to all of the children from where it is defined, such as
    _cpFilterList."""
    
    # First, we look in the right-most object to see if this special
    # attribute is implemented. If not, then we try the previous object,
    # and so on until we reach cherrypy.root. If it's still not there,
    # we use the implementation from this module.
    
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

def _cpGlobalHandler():
    """Default handler for a Request-URI of '*'."""
    response = cherrypy.response
    response.headerMap['Content-Type'] = 'text/plain'
    
    # OPTIONS is defined in HTTP 1.1 and greater
    request = cherrypy.request
    if request.method == 'OPTIONS' and request.version >= 1.1:
        response.headerMap['Allow'] = 'HEAD, GET, POST, PUT, OPTIONS'
    else:
        response.headerMap['Allow'] = 'HEAD, GET, POST'
    return ""
_cpGlobalHandler.exposed = True

def logtime():
    now = datetime.datetime.now()
    month = httptools.monthname[now.month][:3].capitalize()
    return '%02d/%s/%04d:%02d:%02d:%02d' % (
        now.day, month, now.year, now.hour, now.minute, now.second)

def _cpLogAccess():
    """ Default method for logging access """
    
    tmpl = '%(h)s %(l)s %(u)s [%(t)s] "%(r)s" %(s)s %(b)s'
    s = tmpl % {'h': cherrypy.request.remoteHost,
                'l': '-',
                'u': getattr(cherrypy.request, "login", None) or "-",
                't': logtime(),
                'r': cherrypy.request.requestLine,
                's': cherrypy.response.status.split(" ", 1)[0],
                'b': cherrypy.response.headerMap.get('Content-Length', '') or "-",
                }
    
    if cherrypy.config.get('server.logToScreen', True):
        print s
    
    fname = cherrypy.config.get('server.logAccessFile', '')
    if fname:
        f = open(fname, 'ab')
        f.write(s + '\n')
        f.close()


_log_severity_levels = {0: "INFO", 1: "WARNING", 2: "ERROR"}

def _cpLogMessage(msg, context = '', severity = 0):
    """Default method for logging messages (error log).
    
    This is not just for errors! Applications may call this at any time to
    log application-specific information.
    """
    
    level = _log_severity_levels.get(severity, "UNKNOWN")
    
    s = ' '.join((logtime(), context, level, msg))
    
    if cherrypy.config.get('server.logToScreen', True):
        print s
    
    fname = cherrypy.config.get('server.logFile', '')
    #logdir = os.path.dirname(fname)
    #if logdir and not os.path.exists(logdir):
    #    os.makedirs(logdir)
    if fname:
        f = open(fname, 'ab')
        f.write(s + '\n')
        f.close()


_HTTPErrorTemplate = '''<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
  "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html>
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
    <title>%(status)s</title>
    <style type="text/css">
    #poweredBy {
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
    <div id="poweredBy">
    <span>Powered by <a href="http://www.cherrypy.org">Cherrypy %(version)s</a></span>
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
    errorPageFile = cherrypy.config.get('errorPage.%s' % code, '')
    if errorPageFile:
        try:
            template = file(errorPageFile, 'rb').read()
        except:
            m = kwargs['message']
            if m:
                m += "<br />"
            m += ("In addition, the custom error page "
                  "failed:\n<br />%s" % (sys.exc_info()[1]))
            kwargs['message'] = m
    
    return template % kwargs


def _cpOnHTTPError(status, message):
    """ Default _cpOnHTTPError method.
    
    status should be an int.
    """
    tb = formatExc()
    logmsg = ""
    
    if cherrypy.config.get('server.logTracebacks', True):
        logmsg = tb
    if cherrypy.config.get('server.logRequestHeaders', True):
        h = ["  %s: %s" % (k, v) for k, v in cherrypy.request.headers]
        logmsg += 'Request Headers:\n' + '\n'.join(h)
    if logmsg:
        cherrypy.log(logmsg, "HTTP")
    
    if not cherrypy.config.get('server.showTracebacks', False):
        tb = None
    
    response = cherrypy.response
    
    # Remove headers which applied to the original content,
    # but do not apply to the error page.
    for key in ["Accept-Ranges", "Age", "ETag", "Location", "Retry-After",
                "Vary", "Content-Encoding", "Content-Length", "Expires",
                "Content-Location", "Content-MD5", "Last-Modified"]:
        if response.headerMap.has_key(key):
            del response.headerMap[key]
    
    if status != 416:
        # A server sending a response with status code 416 (Requested
        # range not satisfiable) SHOULD include a Content-Range field
        # with a byte-range- resp-spec of "*". The instance-length
        # specifies the current length of the selected resource.
        # A response with status code 206 (Partial Content) MUST NOT
        # include a Content-Range field with a byte-range- resp-spec of "*".
        if response.headerMap.has_key("Content-Range"):
            del response.headerMap["Content-Range"]
    
    # In all cases, finalize will be called after this method,
    # so don't bother cleaning up response values here.
    response.status = status
    response.body = getErrorPage(status, traceback=tb, message=message)
    response.headerMap['Content-Length'] = len(response.body)
    response.headerMap['Content-Type'] = "text/html"
    
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
        content = ''.join([chunk for chunk in response.body])
        l = len(content)
        if l and l < s:
            # IN ADDITION: the response must be written to IE
            # in one chunk or it will still get replaced! Bah.
            response.body = [content + (" " * (s - l))]
        else:
            response.body = [content]
        response.headerMap['Content-Length'] = len(response.body[0])

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

def _cpOnError():
    """ Default _cpOnError method """
    # Allow logging of only *unexpected* HTTPError's.
    if (not cherrypy.config.get('server.logTracebacks', True)
        and cherrypy.config.get('server.logUnhandledTracebacks', True)):
        cherrypy.log(formatExc())
    
    cherrypy.HTTPError(500).set_response()


_cpFilterList = []

