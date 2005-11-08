"""A few utility classes/functions used by CherryPy."""

import sys
import traceback
import time
import cgi

import cherrypy
from cherrypy.lib import httptools


class EmptyClass:
    """ An empty class """
    pass


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
        nameList = ['global_']
    nameList = ['root'] + nameList + ['index']
    
    # Convert the list of names into a list of objects
    node = cherrypy
    objectTrail = []
    for objname in nameList:
        # maps virtual names to Python identifiers (replaces '.' with '_')
        objname = objname.replace('.', '_')
        node = getattr(node, objname, None)
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

def logtime():
    return '%04d/%02d/%02d %02d:%02d:%02d' % time.localtime(time.time())[:6]

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
    """ Default method for logging messages (error log)"""
    
    level = _log_severity_levels.get(severity, "UNKNOWN")
    s = logtime() + ' ' + context + ' ' + level + ' ' + msg
    
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
    if cherrypy.config.get('server.logTracebacks', True):
        cherrypy.log(tb)
    
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
    cherrypy.HTTPError(500).set_response()

_cpFilterList = []

# Filters that are always included
from cherrypy.lib.filter import baseurlfilter, cachefilter, \
    decodingfilter, encodingfilter, gzipfilter, logdebuginfofilter, \
    staticfilter, nsgmlsfilter, tidyfilter, \
    xmlrpcfilter, sessionauthenticatefilter, \
    sessionfilter

# this contains the classes for each filter type
# we do not store the instances here because the test
# suite must reinitilize the filters without restarting
# the server
_cpDefaultFilterClasses = {
    'BaseUrlFilter'      : baseurlfilter.BaseUrlFilter,
    'CacheFilter'        : cachefilter.CacheFilter,
    'DecodingFilter'     : decodingfilter.DecodingFilter,
    'EncodingFilter'     : encodingfilter.EncodingFilter,
    'GzipFilter'         : gzipfilter.GzipFilter,
    'LogDebugInfoFilter' : logdebuginfofilter.LogDebugInfoFilter,
    'NsgmlsFilter'       : nsgmlsfilter.NsgmlsFilter,
    'SessionAuthenticateFilter' : sessionauthenticatefilter.SessionAuthenticateFilter,
    'SessionFilter'      : sessionfilter.SessionFilter,
    'StaticFilter'       : staticfilter.StaticFilter,
    'TidyFilter'         : tidyfilter.TidyFilter,
    'XmlRpcFilter'       : xmlrpcfilter.XmlRpcFilter,
}

# this is where the actuall filter instances are first stored
_cpDefaultFilterInstances = {}

# These are in order for a reason!
# They must be strings matching keys in _cpDefaultFilterClasses
__cpDefaultInputFilters = [
    'CacheFilter',
    'LogDebugInfoFilter',
    'BaseUrlFilter',
    'DecodingFilter',
    'SessionFilter',
    'SessionAuthenticateFilter',
    'StaticFilter',
    'NsgmlsFilter',
    'TidyFilter',
    'XmlRpcFilter',
]

__cpDefaultOutputFilters = [
    'XmlRpcFilter',
    'EncodingFilter',
    'TidyFilter',
    'NsgmlsFilter',
    'LogDebugInfoFilter',
    'GzipFilter',
    'SessionFilter',
    'CacheFilter',
]

# these are the lists cp internally uses to access the filters
# they are populated when _cpInitDefaultFilters is called
_cpDefaultInputFilterList  = []
_cpDefaultOutputFilterList = []

# initilize the default filters
def _cpInitDefaultFilters():
    global _cpDefaultInputFilterList, _cpDefaultOutputFilterList
    global _cpDefaultFilterInstances
    _cpDefaultInputFilterList  = []
    _cpDefaultOutputFilterList = []
    _cpDefaultFilterInstances = {}
    
    for filterName in __cpDefaultInputFilters:
        filterClass = _cpDefaultFilterClasses[filterName]
        filterInstance = _cpDefaultFilterInstances[filterName] = filterClass()
        _cpDefaultInputFilterList.append(filterInstance)
    
    for filterName in __cpDefaultOutputFilters:
        filterClass = _cpDefaultFilterClasses[filterName]
        filterInstance = _cpDefaultFilterInstances.setdefault(filterName, filterClass())
        _cpDefaultOutputFilterList.append(filterInstance)

def _cpInitUserDefinedFilters():
    filtersRoot = cherrypy.config.get('server.filtersRoot', [])
    inputFiltersDict = cherrypy.config.get('server.inputFiltersDict', {})
    outputFiltersDict = cherrypy.config.get('server.outputFiltersDict', {})
    
    if len(filtersRoot) == 0:
        return

    sys.path.extend(filtersRoot)
        
    for filterName, filterClassname in inputFiltersDict.items():
        filterModule = __import__(filterName, globals(),  locals(), [])
        filterClass = getattr(filterModule, filterClassname, None)
        filterInstance = filterClass()
        _cpDefaultInputFilterList.append(filterInstance)

    for filterName, filterClassname in outputFiltersDict.items():
        filterModule = __import__(filterName, globals(),  locals(), [])
        filterClass = getattr(filterModule, filterClassname, None)
        filterInstance = filterClass()
        _cpDefaultOutputFilterList.append(filterInstance)

    # Avoid pollution of the system path
    for path in filtersRoot:
        sys.path.remove(path)


# public domain "unrepr" implementation, found on the web and then improved.
import compiler

def getObj(s):
    s = "a=" + s
    p = compiler.parse(s)
    return p.getChildren()[1].getChildren()[0].getChildren()[1]


class UnknownType(Exception):
    
    # initialize the built-in filters 
    for n in xrange(len(_cpDefaultInputFilterList)):
        try:
            _cpDefaultInputFilterList[n] = _cpDefaultInputFilterList[n]()
        except:
            pass
    
    for n in xrange(len(_cpDefaultOutputFilterList)):
        try:
            _cpDefaultOutputFilterList[n] = _cpDefaultOutputFilterList[n]()
        except:
            pass


class Builder:
    
    def build(self, o):
        m = getattr(self, 'build_' + o.__class__.__name__, None)
        if m is None:
            raise UnknownType(o.__class__.__name__)
        return m(o)
    
    def build_List(self, o):
        return map(self.build, o.getChildren())
    
    def build_Const(self, o):
        return o.value
    
    def build_Dict(self, o):
        d = {}
        i = iter(map(self.build, o.getChildren()))
        for el in i:
            d[el] = i.next()
        return d
    
    def build_Tuple(self, o):
        return tuple(self.build_List(o))
    
    def build_Name(self, o):
        if o.name == 'None':
            return None
        if o.name == 'True':
            return True
        if o.name == 'False':
            return False
        
        # See if the Name is a package or module
        try:
            return modules(o.name)
        except ImportError:
            pass
        
        raise UnknownType(o.name)
    
    def build_Add(self, o):
        real, imag = map(self.build_Const, o.getChildren())
        try:
            real = float(real)
        except TypeError:
            raise UnknownType('Add')
        if not isinstance(imag, complex) or imag.real != 0.0:
            raise UnknownType('Add')
        return real+imag
    
    def build_Getattr(self, o):
        parent = self.build(o.expr)
        return getattr(parent, o.attrname)


def unrepr(s):
    if not s:
        return s
    try:
        return Builder().build(getObj(s))
    except:
        raise cherrypy.WrongUnreprValue(repr(s))

def modules(modulePath):
    """Load a module and retrieve a reference to that module."""
    try:
        mod = sys.modules[modulePath]
        if mod is None:
            raise KeyError()
    except KeyError:
        # The last [''] is important.
        mod = __import__(modulePath, globals(), locals(), [''])
    return mod

def attributes(fullAttributeName):
    """Load a module and retrieve an attribute of that module."""
    
    # Parse out the path, module, and attribute
    lastDot = fullAttributeName.rfind(u".")
    attrName = fullAttributeName[lastDot + 1:]
    modPath = fullAttributeName[:lastDot]
    
    aMod = modules(modPath)
    # Let an AttributeError propagate outward.
    try:
        attr = getattr(aMod, attrName)
    except AttributeError:
        raise AttributeError("'%s' object has no attribute '%s'"
                             % (modPath, attrName))
    
    # Return a reference to the attribute.
    return attr
