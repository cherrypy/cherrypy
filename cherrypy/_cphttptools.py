"""CherryPy core request/response handling."""

import Cookie
import os
import sys
import types

import cherrypy
from cherrypy import _cputil, _cpcgifs, _cpwsgiserver
from cherrypy.filters import applyFilters
from cherrypy.lib import cptools, httptools


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
        
        When run() is done, the returned object should have 3 attributes:
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
            self.headerMap = httptools.HeaderMap()
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
        method, path, qs, proto = httptools.parseRequestLine(rl)
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
        self.version = httptools.Version.from_http(self.protocol)
        server_v = cherrypy.config.get("server.protocolVersion", "HTTP/1.0")
        server_v = httptools.Version.from_http(server_v)
        
        # cherrypy.response.version should be used to determine whether or
        # not to include a given HTTP/1.1 feature in the response content.
        cherrypy.response.version = min(self.version, server_v)
        
        self.paramMap = httptools.parseQueryString(self.queryString)
        
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
        # This feature is deprecated in 2.2 and will be removed in 2.3.
        self._originalParamMap = self.paramMap.copy()
        
        if self.version >= "1.1":
            # All Internet-based HTTP/1.1 servers MUST respond with a 400
            # (Bad Request) status code to any HTTP/1.1 request message
            # which lacks a Host header field.
            if not self.headerMap.has_key("Host"):
                msg = "HTTP/1.1 requires a 'Host' request header."
                raise cherrypy.HTTPError(400, msg)
        self.base = "%s://%s" % (self.scheme, self.headerMap.get('Host', ''))
    
    def _get_original_param_map(self):
        # This feature is deprecated in 2.2 and will be removed in 2.3.
        return self._originalParamMap
    originalParamMap = property(_get_original_param_map,
                        doc="Deprecated. A copy of the original paramMap.")
    
    def _get_browserUrl(self):
        url = self.base + self.path
        if self.queryString:
            url += '?' + self.queryString
        return url
    browserUrl = property(_get_browserUrl,
                          doc="The URL as entered in a browser (read-only).")
    
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
            self.paramMap.update(httptools.paramsFromCGIForm(forms))
    
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
        
        objectTrail = _cputil.get_object_trail(objectpath)
        names = [name for name, candidate in objectTrail]
        
        # Try successive objects
        for i in xrange(len(objectTrail) - 1, -1, -1):
            
            name, candidate = objectTrail[i]
            
            # Try a "default" method on the current leaf.
            defhandler = getattr(candidate, "default", None)
            if callable(defhandler) and getattr(defhandler, 'exposed', False):
                return defhandler, names[:i+1] + ["default"], names[i+1:-1]
            
            # Uncomment the next line to restrict positional params to "default".
            # if i < len(objectTrail) - 2: continue
            
            # Try the current leaf.
            if callable(candidate) and getattr(candidate, 'exposed', False):
                if i == len(objectTrail) - 1:
                    # We found the extra ".index". Check if the original path
                    # had a trailing slash (otherwise, do a redirect).
                    if not objectpath.endswith('/'):
                        atoms = self.browserUrl.split("?", 1)
                        newUrl = atoms.pop(0) + '/'
                        if atoms:
                            newUrl += "?" + atoms[0]
                        raise cherrypy.HTTPRedirect(newUrl)
                return candidate, names[:i+1], names[i+1:-1]
        
        # Not found at any node
        if objectpath.endswith("favicon.ico"):
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
            raise cherrypy.NotFound(objectpath)


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


class Response(object):
    """An HTTP Response."""
    
    def __init__(self):
        self.status = None
        self.headers = None
        self.body = None
        
        self.headerMap = httptools.HeaderMap()
        self.headerMap.update({
            "Content-Type": "text/html",
            "Server": "CherryPy/" + cherrypy.__version__,
            "Date": httptools.HTTPDate(),
            "Set-Cookie": [],
            "Content-Length": None
        })
        self.simpleCookie = Cookie.SimpleCookie()
    
    def finalize(self):
        """Transform headerMap (and cookies) into cherrypy.response.headers."""
        
        try:
            code, reason, _ = httptools.validStatus(self.status)
        except ValueError, x:
            raise cherrypy.HTTPError(500, x.args[0])
        
        self.status = "%s %s" % (code, reason)
        
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
        
        # Headers
        headers = []
        for key, valueList in self.headerMap.iteritems():
            order = _header_order_map.get(key, 3)
            if not isinstance(valueList, list):
                valueList = [valueList]
            for value in valueList:
                headers.append((order, (key, str(value))))
        # RFC 2616: '... it is "good practice" to send general-header
        # fields first, followed by request-header or response-header
        # fields, and ending with the entity-header fields.'
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
