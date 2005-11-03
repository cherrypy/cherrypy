"""CherryPy core request/response handling."""

import cgi
import Cookie
import os
import re
import sys
import types

import cherrypy
from cherrypy import _cputil, _cpcgifs, _cpwsgiserver
from cherrypy.lib import cptools


class Version(object):
    
    """A version, such as "2.1 beta 3", which can be compared atom-by-atom.
    
    If a string is provided to the constructor, it will be split on word
    boundaries; that is, "1.4.13 beta 9" -> ["1", "4", "13", "beta", "9"].
    
    Comparisons are performed atom-by-atom, numerically if both atoms are
    numeric. Therefore, "2.12" is greater than "2.4", and "3.0 beta" is
    greater than "3.0 alpha" (only because "b" > "a"). If an atom is
    provided in one Version and not another, the longer Version is
    greater than the shorter, that is: "4.8 alpha" > "4.8".
    """
    
    def __init__(self, atoms):
        """A Version object. A str argument will be split on word boundaries."""
        if isinstance(atoms, basestring):
            self.atoms = re.split(r'\W', atoms)
        else:
            self.atoms = [str(x) for x in atoms]
    
    def from_http(cls, version_str):
        """Return a Version object from the given 'HTTP/x.y' string."""
        return cls(version_str[5:])
    from_http = classmethod(from_http)
    
    def to_http(self):
        """Return a 'HTTP/x.y' string for this Version object."""
        return "HTTP/%s.%s" % tuple(self.atoms[:2])
    
    def __str__(self):
        return ".".join([str(x) for x in self.atoms])
    
    def __cmp__(self, other):
        cls = self.__class__
        if not isinstance(other, cls):
            # Try to coerce other to a Version instance.
            other = cls(other)
        
        index = 0
        while index < len(self.atoms) and index < len(other.atoms):
            mine, theirs = self.atoms[index], other.atoms[index]
            if mine.isdigit() and theirs.isdigit():
                mine, theirs = int(mine), int(theirs)
            if mine < theirs:
                return -1
            if mine > theirs:
                return 1
            index += 1
        if index < len(other.atoms):
            return -1
        if index < len(self.atoms):
            return 1
        return 0


class Request(object):
    """An HTTP request."""
    
    def __init__(self, remoteAddr, remotePort, remoteHost, scheme="http"):
        """Populate a new Request object.
        
        remoteAddr should be the client IP address
        remotePort should be the client Port
        remoteHost should be string of the client's IP address.
        scheme should be a string, either "http" or "https".
        """
        self.remoteAddr = remoteAddr
        self.remotePort = remotePort
        self.remoteHost = remoteHost
        self.scheme = scheme
    
    def run(self, requestLine, headers, rfile):
        """Process the Request.
        
        requestLine should be of the form "GET /path HTTP/1.0".
        headers should be a list of (name, value) tuples.
        rfile should be a file-like object containing the HTTP request
            entity.
        
        When run() is done, cherrypy.response should have 3 attributes:
          status, e.g. "200 OK"
          headers, a list of (name, value) tuples
          body, an iterable yielding strings
        
        Consumer code (HTTP servers) should then access these response
        attributes to build the outbound stream.
        
        """
        if cherrypy.profiler:
            cherrypy.profiler.run(self._run, requestLine, headers, rfile)
        else:
            self._run(requestLine, headers, rfile)
        return cherrypy.response
    
    def _run(self, requestLine, headers, rfile):
        
        try:
            self.headers = headers
            self.headerMap = cptools.HeaderMap()
            self.simpleCookie = Cookie.SimpleCookie()
            self.rfile = rfile
            
            # This has to be done very early in the request process,
            # because request.objectPath is used for config lookups
            # right away.
            self.processRequestLine(requestLine)
            
            try:
                applyFilters('onStartResource')
                
                try:
                    self.processHeaders()
                    
                    applyFilters('beforeRequestBody')
                    if self.processRequestBody:
                        self.processBody()
                    
                    applyFilters('beforeMain')
                    if cherrypy.response.body is None:
                        self.main()
                    
                    applyFilters('beforeFinalize')
                    cherrypy.response.finalize()
                except cherrypy.RequestHandled:
                    pass
                except (cherrypy.HTTPRedirect, cherrypy.HTTPError), inst:
                    # For an HTTPRedirect or HTTPError (including NotFound),
                    # we don't go through the regular mechanism:
                    # we return the redirect or error page immediately
                    inst.set_response()
                    applyFilters('beforeFinalize')
                    cherrypy.response.finalize()
            finally:
                applyFilters('onEndResource')
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            cherrypy.response.handleError(sys.exc_info())
        
        if self.method == "HEAD":
            # HEAD requests MUST NOT return a message-body in the response.
            cherrypy.response.body = []
        
        _cputil.getSpecialAttribute("_cpLogAccess")()
    
    def processRequestLine(self, requestLine):
        self.requestLine = rl = requestLine.strip()
        method, path, qs, proto = cptools.parseRequestLine(rl)
        if path == "*":
            path = "global"
        
        self.method = method
        self.processRequestBody = method in ("POST", "PUT")
        
        self.path = path
        self.queryString = qs
        self.protocol = proto
        
        # Change objectPath in filters to change
        # the object that will get rendered
        self.objectPath = path
    
    def processHeaders(self):
        # Compare request and server HTTP versions, in case our server does
        # not support the requested version. We can't tell the server what
        # version number to write in the response, so we limit our output
        # to min(req, server). We want the following output:
        #     request    server     actual written   supported response
        #     version    version   response version  feature set (resp.v)
        # a     1.0        1.0           1.0                1.0
        # b     1.0        1.1           1.1                1.0
        # c     1.1        1.0           1.0                1.0
        # d     1.1        1.1           1.1                1.1
        # Notice that, in (b), the response will be "HTTP/1.1" even though
        # the client only understands 1.0. RFC 2616 10.5.6 says we should
        # only return 505 if the _major_ version is different.
        
        # cherrypy.request.version == request.protocol in a Version instance.
        self.version = Version.from_http(self.protocol)
        server_v = cherrypy.config.get("server.protocolVersion", "HTTP/1.0")
        server_v = Version.from_http(server_v)
        
        # cherrypy.response.version should be used to determine whether or
        # not to include a given HTTP/1.1 feature in the response content.
        cherrypy.response.version = min(self.version, server_v)
        
        self.paramMap = cptools.parseQueryString(self.queryString)
        
        # Process the headers into self.headerMap
        for name, value in self.headers:
            value = value.strip()
            # Warning: if there is more than one header entry for cookies (AFAIK,
            # only Konqueror does that), only the last one will remain in headerMap
            # (but they will be correctly stored in request.simpleCookie).
            self.headerMap[name] = value
            
            # Handle cookies differently because on Konqueror, multiple
            # cookies come on different lines with the same key
            if name.title() == 'Cookie':
                self.simpleCookie.load(value)
        
        # Save original values (in case they get modified by filters)
        self.originalParamMap = self.paramMap
        
        if self.version >= "1.1":
            # All Internet-based HTTP/1.1 servers MUST respond with a 400
            # (Bad Request) status code to any HTTP/1.1 request message
            # which lacks a Host header field.
            if not self.headerMap.has_key("Host"):
                msg = "HTTP/1.1 requires a 'Host' request header."
                raise cherrypy.HTTPError(400, msg)
        self.base = "%s://%s" % (self.scheme, self.headerMap.get('Host', ''))
        self.browserUrl = self.base + self.path
        if self.queryString:
            self.browserUrl += '?' + self.queryString
    
    def processBody(self):
        # Create a copy of headerMap with lowercase keys because
        # FieldStorage doesn't work otherwise
        lowerHeaderMap = {}
        for key, value in self.headerMap.items():
            lowerHeaderMap[key.lower()] = value
        
        # FieldStorage only recognizes POST, so fake it.
        methenv = {'REQUEST_METHOD': "POST"}
        try:
            forms = _cpcgifs.FieldStorage(fp=self.rfile,
                                          headers=lowerHeaderMap,
                                          environ=methenv,
                                          keep_blank_values=1)
        except _cpwsgiserver.MaxSizeExceeded:
            # Post data is too big
            raise cherrypy.HTTPError(413)
        
        if forms.file:
            # request body was a content-type other than form params.
            self.body = forms.file
        else:
            self.paramMap.update(cptools.paramsFromCGIForm(forms))
    
    def main(self, path=None):
        """Obtain and set cherrypy.response.body from a page handler."""
        if path is None:
            path = self.objectPath
        
        while True:
            try:
                page_handler, object_path, virtual_path = self.mapPathToObject(path)
                
                # Remove "root" from object_path and join it to get objectPath
                self.objectPath = '/' + '/'.join(object_path[1:])
                body = page_handler(*virtual_path, **self.paramMap)
                cherrypy.response.body = iterable(body)
                return
            except cherrypy.InternalRedirect, x:
                # Try again with the new path
                path = x.path
    
    def mapPathToObject(self, objectpath):
        """For path, return the corresponding exposed callable (or raise NotFound).
        
        path should be a "relative" URL path, like "/app/a/b/c". Leading and
        trailing slashes are ignored.
        
        Traverse path:
        for /a/b?arg=val, we'll try:
          root.a.b.index -> redirect to /a/b/?arg=val
          root.a.b.default(arg='val') -> redirect to /a/b/?arg=val
          root.a.b(arg='val')
          root.a.default('b', arg='val')
          root.default('a', 'b', arg='val')
        
        The target method must have an ".exposed = True" attribute.
        
        """
        
        # Remove leading and trailing slash
        tpath = objectpath.strip("/")
        
        if not tpath:
            objectPathList = []
        else:
            objectPathList = tpath.split('/')
        if objectPathList == ['global']:
            objectPathList = ['global_']
        objectPathList = ['root'] + objectPathList + ['index']
        
        if getattr(cherrypy, "debug", None):
            cherrypy.log("  Attempting to map path: %s using %s"
                         % (tpath, objectPathList), "DEBUG")
        
        # Try successive objects... (and also keep the remaining object list)
        isFirst = True
        isSecond = False
        foundIt = False
        virtualPathList = []
        while objectPathList:
            if isFirst or isSecond:
                # Only try this for a.b.index() or a.b()
                candidate = self.getObjFromPath(objectPathList)
                if callable(candidate) and getattr(candidate, 'exposed', False):
                    foundIt = True
                    break
            # Couldn't find the object: pop one from the list and try "default"
            lastObj = objectPathList.pop()
            if (not isFirst) or (not tpath):
                virtualPathList.insert(0, lastObj)
                objectPathList.append('default')
                candidate = self.getObjFromPath(objectPathList)
                if callable(candidate) and getattr(candidate, 'exposed', False):
                    foundIt = True
                    break
                objectPathList.pop() # Remove "default"
            if isSecond:
                isSecond = False
            if isFirst:
                isFirst = False
                isSecond = True
        
        # Check results of traversal
        if not foundIt:
            if tpath.endswith("favicon.ico"):
                # Use CherryPy's default favicon.ico. If developers really,
                # really want no favicon, they can make a dummy method
                # that raises NotFound.
                icofile = os.path.join(os.path.dirname(__file__), "favicon.ico")
                cptools.serveFile(icofile)
                applyFilters('beforeFinalize')
                cherrypy.response.finalize()
                raise cherrypy.RequestHandled()
            else:
                # We didn't find anything
                if getattr(cherrypy, "debug", None):
                    cherrypy.log("    NOT FOUND", "DEBUG")
                raise cherrypy.NotFound(objectpath)
        
        if isFirst:
            # We found the extra ".index". Check if the original path
            # had a trailing slash (otherwise, do a redirect).
            if not objectpath.endswith('/'):
                atoms = self.browserUrl.split("?", 1)
                newUrl = atoms.pop(0) + '/'
                if atoms:
                    newUrl += "?" + atoms[0]
                if getattr(cherrypy, "debug", None):
                    cherrypy.log("    Found: redirecting to %s" % newUrl, "DEBUG")
                raise cherrypy.HTTPRedirect(newUrl)
        
        if getattr(cherrypy, "debug", None):
            cherrypy.log("    Found: %s" % candidate, "DEBUG")
        return candidate, objectPathList, virtualPathList
    
    def getObjFromPath(self, objPathList):
        """For a given objectPathList, return the object (or None).
        
        objPathList should be a list of the form: ['root', 'a', 'b', 'index'].
        """
        
        root = cherrypy
        for objname in objPathList:
            # maps virtual filenames to Python identifiers (substitutes '.' for '_')
            objname = objname.replace('.', '_')
            if getattr(cherrypy, "debug", None):
                cherrypy.log("    Trying: %s.%s" % (root, objname), "DEBUG")
            root = getattr(root, objname, None)
            if root is None:
                return None
        return root


general_header_fields = ["Cache-Control", "Connection", "Date", "Pragma",
                         "Trailer", "Transfer-Encoding", "Upgrade", "Via",
                         "Warning"]
response_header_fields = ["Accept-Ranges", "Age", "ETag", "Location",
                          "Proxy-Authenticate", "Retry-After", "Server",
                          "Vary", "WWW-Authenticate"]
entity_header_fields = ["Allow", "Content-Encoding", "Content-Language",
                        "Content-Length", "Content-Location", "Content-MD5",
                        "Content-Range", "Content-Type", "Expires",
                        "Last-Modified"]

_header_order_map = {}
for _ in general_header_fields:
    _header_order_map[_] = 0
for _ in response_header_fields:
    _header_order_map[_] = 1
for _ in entity_header_fields:
    _header_order_map[_] = 2

_ie_friendly_error_sizes = {400: 512, 403: 256, 404: 512, 405: 256,
                            406: 512, 408: 512, 409: 512, 410: 256,
                            500: 512, 501: 512, 505: 512,
                            }


class Response(object):
    """An HTTP Response."""
    
    def __init__(self):
        self.status = None
        self.headers = None
        self.body = None
        
        self.headerMap = cptools.HeaderMap()
        self.headerMap.update({
            "Content-Type": "text/html",
            "Server": "CherryPy/" + cherrypy.__version__,
            "Date": cptools.HTTPDate(),
            "Set-Cookie": [],
            "Content-Length": None
        })
        self.simpleCookie = Cookie.SimpleCookie()
    
    def finalize(self):
        """Transform headerMap (and cookies) into cherrypy.response.headers."""
        
        code, reason, _ = cptools.validStatus(self.status)
        self.status = "%s %s" % (code, reason)
        
        if self.body is None:
            self.body = []
        
        stream = cherrypy.config.get("streamResponse", False)
        # OPTIONS requests MUST include a Content-Length of 0 if no body.
        # Just punt and figure Content-Length for all OPTIONS requests.
        if cherrypy.request.method == "OPTIONS":
            stream = False
        
        if stream:
            try:
                del self.headerMap['Content-Length']
            except KeyError:
                pass
        else:
            # Responses which are not streamed should have a Content-Length,
            # but allow user code to set Content-Length if desired.
            if self.headerMap.get('Content-Length') is None:
                content = ''.join([chunk for chunk in self.body])
                self.body = [content]
                self.headerMap['Content-Length'] = len(content)
        
        # For some statuses, Internet Explorer 5+ shows "friendly error messages"
        # instead of our response.body if the body is smaller than a given size.
        # Fix this by returning a body over that size (by adding whitespace).
        # See http://support.microsoft.com/kb/q218155/
        s = int(self.status.split(" ")[0])
        s = _ie_friendly_error_sizes.get(s, 0)
        if s:
            s += 1
            # Since we are issuing an HTTP error status, we assume that
            # the entity is short, and we should just collapse it.
            content = ''.join([chunk for chunk in self.body])
            self.body = [content]
            l = len(content)
            if l and l < s:
                # IN ADDITION: the response must be written to IE
                # in one chunk or it will still get replaced! Bah.
                self.body = [self.body[0] + (" " * (s - l))]
                self.headerMap['Content-Length'] = s
        
        # Headers
        headers = []
        for key, valueList in self.headerMap.iteritems():
            order = _header_order_map.get(key, 3)
            if not isinstance(valueList, list):
                valueList = [valueList]
            for value in valueList:
                headers.append((order, (key, str(value))))
        # RFC 2616: '... it is "good practice" to send general-header fields
        # first, followed by request-header or response-header fields, and
        # ending with the entity-header fields.'
        headers.sort()
        self.headers = [item[1] for item in headers]
        
        cookie = self.simpleCookie.output()
        if cookie:
            lines = cookie.split("\n")
            for line in lines:
                name, value = line.split(": ", 1)
                self.headers.append((name, value))
    
    dbltrace = "\n===First Error===\n\n%s\n\n===Second Error===\n\n%s\n\n"
    
    def handleError(self, exc):
        """Set status, headers, and body when an unanticipated error occurs."""
        try:
            applyFilters('beforeErrorResponse')
           
            # _cpOnError will probably change self.body.
            # It may also change the headerMap, etc.
            _cputil.getSpecialAttribute('_cpOnError')()
            
            self.finalize()
            
            applyFilters('afterErrorResponse')
            return
        except cherrypy.HTTPRedirect, inst:
            try:
                inst.set_response()
                self.finalize()
                return
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                # Fall through to the second error handler
                pass
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            # Fall through to the second error handler
            pass
        
        # Failure in _cpOnError, error filter, or finalize.
        # Bypass them all.
        if cherrypy.config.get('server.showTracebacks', False):
            body = self.dbltrace % (_cputil.formatExc(exc),
                                    _cputil.formatExc())
        else:
            body = ""
        self.setBareError(body)
    
    def setBareError(self, body=None):
        self.status, self.headers, self.body = _cputil.bareError(body)


def iterable(body):
    """Convert the given body to an iterable object."""
    if isinstance(body, types.FileType):
        body = cptools.fileGenerator(body)
    elif isinstance(body, types.GeneratorType):
        body = flattener(body)
    elif isinstance(body, basestring):
        # strings get wrapped in a list because iterating over a single
        # item list is much faster than iterating over every character
        # in a long string.
        body = [body]
    elif body is None:
        body = [""]
    return body

def flattener(input):
    """Yield the given input, recursively iterating over each result (if needed)."""
    for x in input:
        if not isinstance(x, types.GeneratorType):
            yield x
        else:
            for y in flattener(x):
                yield y 

def applyFilters(methodName):
    """Execute the given method for all registered filters."""
    if methodName in ('onStartResource', 'beforeRequestBody', 'beforeMain'):
        filterList = (_cputil._cpDefaultInputFilterList +
                      _cputil.getSpecialAttribute('_cpFilterList'))
    elif methodName in ('beforeFinalize', 'onEndResource',
                'beforeErrorResponse', 'afterErrorResponse'):
        filterList = (_cputil.getSpecialAttribute('_cpFilterList') +
                      _cputil._cpDefaultOutputFilterList)
    else:
        assert False # Wrong methodName for the filter
    for filter in filterList:
        method = getattr(filter, methodName, None)
        if method:
            method()
