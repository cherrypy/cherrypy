"""
Copyright (c) 2004, CherryPy Team (team@cherrypy.org)
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, 
are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice, 
      this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice, 
      this list of conditions and the following disclaimer in the documentation 
      and/or other materials provided with the distribution.
    * Neither the name of the CherryPy Team nor the names of its contributors 
      may be used to endorse or promote products derived from this software 
      without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND 
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED 
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE 
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE 
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL 
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR 
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER 
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, 
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE 
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

"""
Common Service Code for CherryPy
"""

import urllib, os, sys, time, types, cgi, re
import mimetypes, Cookie
from urlparse import urlparse

import cherrypy
from cherrypy import _cputil, _cpcgifs

from BaseHTTPServer import BaseHTTPRequestHandler
responseCodes = BaseHTTPRequestHandler.responses

mimetypes.types_map['.dwg']='image/x-dwg'
mimetypes.types_map['.ico']='image/x-icon'


weekdayname = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
monthname = [None, 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

def httpdate(dt=None):
    """Return the given time.struct_time as a string in RFC 1123 format.
    
    If no arguments are provided, the current time (as determined by
    time.gmtime() is used).
    
    RFC 2616: "[Concerning RFC 1123, RFC 850, asctime date formats]...
    HTTP/1.1 clients and servers that parse the date value MUST
    accept all three formats (for compatibility with HTTP/1.0),
    though they MUST only generate the RFC 1123 format for
    representing HTTP-date values in header fields."
    
    RFC 1945 (HTTP/1.0) requires the same.
    
    """
    
    if dt is None:
        dt = time.gmtime()
    
    year, month, day, hh, mm, ss, wd, y, z = dt
    # Is "%a, %d %b %Y %H:%M:%S GMT" better or worse?
    return ("%s, %02d %3s %4d %02d:%02d:%02d GMT" %
            (weekdayname[wd], day, monthname[month], year, hh, mm, ss))


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


class KeyTitlingDict(dict):
    
    """A dict subclass which changes each key to str(key).title()
    
    This allows response headers to be case-insensitive and
    avoid duplicates.
    
    """
    
    def __getitem__(self, key):
        return dict.__getitem__(self, str(key).title())
    
    def __setitem__(self, key, value):
        dict.__setitem__(self, str(key).title(), value)
    
    def __delitem__(self, key):
        dict.__delitem__(self, str(key).title())
    
    def __contains__(self, item):
        return dict.__contains__(self, str(item).title())
    
    def get(self, key, default=None):
        return dict.get(self, str(key).title(), default)
    
    def has_key(self, key):
        return dict.has_key(self, str(key).title())
    
    def update(self, E):
        for k in E.keys():
            self[str(k).title()] = E[k]
    
    def fromkeys(cls, seq, value=None):
        newdict = cls()
        for k in seq:
            newdict[str(k).title()] = value
        return newdict
    fromkeys = classmethod(fromkeys)
    
    def setdefault(key, x=None):
        key = str(key).title()
        try:
            return self[key]
        except KeyError:
            self[key] = x
            return x
    
    def pop(self, key, default):
        return dict.pop(self, str(key).title(), default)


class Request(object):
    
    """Process an HTTP request and set cherrypy.response attributes."""
    
    def __init__(self, clientAddress, remoteHost, requestLine, headers,
                 rfile, scheme="http"):
        """Populate a new Request object.
        
        clientAddress and remoteHost should be IP address strings.
        requestLine should be of the form "GET /path HTTP/1.0".
        headers should be a list of (name, value) tuples.
        rfile should be a file-like object containing the HTTP request
            entity.
        scheme should be a string, either "http" or "https".
        
        When __init__ is done, cherrypy.response should have 3 attributes:
          status, e.g. "200 OK"
          headers, a list of (name, value) tuples
          body, an iterable yielding strings
        
        Consumer code (HTTP servers) should then access these response
        attributes to build the outbound stream.
        
        """
        
        cherrypy.request.method = ""
        cherrypy.request.requestLine = requestLine.strip()
        self.parseFirstLine()
        
        self.requestHeaders = headers
        
        # Prepare cherrypy.request variables
        cherrypy.request.remoteAddr = clientAddress
        cherrypy.request.remoteHost = remoteHost
        cherrypy.request.paramList = [] # Only used for Xml-Rpc
        cherrypy.request.headerMap = {}
        cherrypy.request.simpleCookie = Cookie.SimpleCookie()
        cherrypy.request.rfile = rfile
        cherrypy.request.scheme = scheme
        
        # Prepare cherrypy.response variables
        cherrypy.response.status = None
        cherrypy.response.headers = None
        cherrypy.response.body = None
        
        cherrypy.response.headerMap = KeyTitlingDict()
        cherrypy.response.headerMap.update({
            "Content-Type": "text/html",
            "Server": "CherryPy/" + cherrypy.__version__,
            "Date": httpdate(),
            "Set-Cookie": [],
            "Content-Length": None
        })
        cherrypy.response.simpleCookie = Cookie.SimpleCookie()
        
        self.run()
        
        if cherrypy.request.method == "HEAD":
            # HEAD requests MUST NOT return a message-body in the response.
            cherrypy.response.body = []
        
        _cputil.getSpecialAttribute("_cpLogAccess")()
    
    def parseFirstLine(self):
        # This has to be done very early in the request process,
        # because request.path is used for config lookups right away.
        req = cherrypy.request
        
        # Parse first line
        req.method, path, req.protocol = req.requestLine.split()
        req.processRequestBody = req.method in ("POST", "PUT")
        
        # separate the queryString, or set it to "" if not found
        if "?" in path:
            path, req.queryString = path.split("?", 1)
        else:
            path, req.queryString = path, ""
        
        # Unquote the path (e.g. "/this%20path" -> "this path").
        # http://www.w3.org/Protocols/rfc2616/rfc2616-sec5.html#sec5.1.2
        # Note that cgi.parse_qs will decode the querystring for us.
        path = urllib.unquote(path)
        
        if path == "*":
            # "...the request does not apply to a particular resource,
            # but to the server itself". See
            # http://www.w3.org/Protocols/rfc2616/rfc2616-sec5.html#sec5.1.2
            path = "global"
        elif not path.startswith("/"):
            # path is an absolute path (including "http://host.domain.tld");
            # convert it to a relative path, so configMap lookups work. This
            # default method assumes all hosts are valid for this server.
            scheme, location, p, pm, q, f = urlparse(path)
            path = path[len(scheme + "://" + location):]
        
        # Save original value (in case it gets modified by filters)
        req.path = req.originalPath = path
        
        # Change objectPath in filters to change
        # the object that will get rendered
        req.objectPath = None
    
    def run(self):
        """Process the Request."""
        try:
            try:
                applyFilters('onStartResource')
                
                try:
                    self.processRequestHeaders()
                    
                    applyFilters('beforeRequestBody')
                    if cherrypy.request.processRequestBody:
                        self.processRequestBody()
                    
                    applyFilters('beforeMain')
                    if cherrypy.response.body is None:
                        main()
                    
                    applyFilters('beforeFinalize')
                    finalize()
                except cherrypy.RequestHandled:
                    pass
                except cherrypy.HTTPRedirect, inst:
                    # For an HTTPRedirect, we don't go through the regular
                    # mechanism: we return the redirect immediately
                    inst.set_response()
                    finalize()
            finally:
                applyFilters('onEndResource')
        except:
            # This includes HTTPClientError and NotFound
            handleError(sys.exc_info())
    
    def processRequestHeaders(self):
        req = cherrypy.request
        
        # Compare request and server HTTP versions, in case our server does
        # not support the requested version. We can't tell the server what
        # version number to write in the response, so we limit our output
        # to min(req, server). We want the following output:
        #   request version   server version   response version   features
        # a       1.0              1.0               1.0            1.0
        # b       1.0              1.1               1.1            1.0
        # c       1.1              1.0               1.0            1.0
        # d       1.1              1.1               1.1            1.1
        # Notice that, in (b), the response will be "HTTP/1.1" even though
        # the client only understands 1.0. RFC 2616 10.5.6 says we should
        # only return 505 if the _major_ version is different.
        request_v = Version.from_http(req.protocol)
        server_v = cherrypy.config.get("server.protocolVersion", "HTTP/1.0")
        server_v = Version.from_http(server_v)
        cherrypy.request.version = min(request_v, server_v)
        
        # build a paramMap dictionary from queryString
        if re.match(r"[0-9]+,[0-9]+", req.queryString):
            # Server-side image map. Map the coords to 'x' and 'y'
            # (like CGI::Request does).
            pm = req.queryString.split(",")
            pm = {'x': int(pm[0]), 'y': int(pm[1])}
        else:
            pm = cgi.parse_qs(req.queryString, keep_blank_values=True)
            for key, val in pm.items():
                if len(val) == 1:
                    pm[key] = val[0]
        req.paramMap = pm
        
        # Process the headers into request.headerMap
        for name, value in self.requestHeaders:
            name = name.title()
            value = value.strip()
            # Warning: if there is more than one header entry for cookies (AFAIK,
            # only Konqueror does that), only the last one will remain in headerMap
            # (but they will be correctly stored in request.simpleCookie).
            req.headerMap[name] = value
            
            # Handle cookies differently because on Konqueror, multiple
            # cookies come on different lines with the same key
            if name == 'Cookie':
                req.simpleCookie.load(value)
        
        # Write a message to the error.log only if there is no access.log.
        # This is only here for backwards-compatibility (with the time
        # before the access.log existed), and should be removed in CP 2.2.
        fname = cherrypy.config.get('server.logAccessFile', '')
        if not fname:
            msg = "%s - %s" % (req.remoteAddr, req.requestLine)
            cherrypy.log(msg, "HTTP")
        
        # Save original values (in case they get modified by filters)
        req.originalParamMap = req.paramMap
        req.originalParamList = req.paramList
        
        if cherrypy.request.version >= "1.1":
            # All Internet-based HTTP/1.1 servers MUST respond with a 400
            # (Bad Request) status code to any HTTP/1.1 request message
            # which lacks a Host header field.
            if not req.headerMap.has_key("Host"):
                cherrypy.response.status = 400
                cherrypy.response.body = ["HTTP/1.1 requires a 'Host' request header."]
                finalize()
                raise cherrypy.RequestHandled()
        req.base = "%s://%s" % (req.scheme, req.headerMap.get('Host', ''))
        req.browserUrl = req.base + req.path
    
    def processRequestBody(self):
        req = cherrypy.request
        
        # Create a copy of headerMap with lowercase keys because
        # FieldStorage doesn't work otherwise
        lowerHeaderMap = {}
        for key, value in req.headerMap.items():
            lowerHeaderMap[key.lower()] = value
        
        # FieldStorage only recognizes POST, so fake it.
        methenv = {'REQUEST_METHOD': "POST"}
        forms = _cpcgifs.FieldStorage(fp=req.rfile,
                                      headers=lowerHeaderMap,
                                      environ=methenv,
                                      keep_blank_values=1)
        
        if forms.file:
            # request body was a content-type other than form params.
            cherrypy.request.body = forms.file
        else:
            for key in forms.keys():
                valueList = forms[key]
                if isinstance(valueList, list):
                    req.paramMap[key] = []
                    for item in valueList:
                        if item.filename is not None:
                            value = item # It's a file upload
                        else:
                            value = item.value # It's a regular field
                        req.paramMap[key].append(value)
                else:
                    if valueList.filename is not None:
                        value = valueList # It's a file upload
                    else:
                        value = valueList.value # It's a regular field
                    req.paramMap[key] = value


# Error handling

dbltrace = """
=====First Error=====

%s

=====Second Error=====

%s

"""

def handleError(exc):
    """Set status, headers, and body when an error occurs."""
    try:
        applyFilters('beforeErrorResponse')
        
        # _cpOnError will probably change cherrypy.response.body.
        # It may also change the headerMap, etc.
        _cputil.getSpecialAttribute('_cpOnError')()
        
        finalize()
        
        applyFilters('afterErrorResponse')
    except:
        # Failure in _cpOnError, error filter, or finalize.
        # Bypass them all.
        defaultOn = (cherrypy.config.get('server.environment') == 'development')
        if cherrypy.config.get('showTracebacks', defaultOn):
            body = dbltrace % (_cputil.formatExc(exc), _cputil.formatExc())
        else:
            body = ""
        resp = cherrypy.response
        resp.status, resp.headers, resp.body = bareError(body)


def bareError(extrabody=None):
    """Produce status, headers, body for a critical error.
    
    Returns a triple without calling any other questionable functions,
    so it should be as error-free as possible. Call it from an HTTP server
    if you get errors after Request() is done.
    
    If extrabody is None, a friendly but rather unhelpful error message
    is set in the body. If extrabody is a string, it will be appended
    as-is to the body.
    """
    
    body = "Unrecoverable error in the server."
    if extrabody is not None:
        body += "\n" + extrabody
    return ("500 Internal Server Error",
            [('Content-Type', 'text/plain'),
             ('Content-Length', str(len(body)))],
            [body])



# Response functions

def main(path=None):
    """Obtain and set cherrypy.response.body from a page handler."""
    if path is None:
        path = cherrypy.request.objectPath or cherrypy.request.path
    
    while True:
        try:
            func, objectPathList, virtualPathList = mapPathToObject(path)
            
            # Remove "root" from objectPathList and join it to get objectPath
            cherrypy.request.objectPath = '/' + '/'.join(objectPathList[1:])
            try:
                body = func(*(virtualPathList + cherrypy.request.paramList),
                            **(cherrypy.request.paramMap))
            except TypeError, x:
                m = re.match(r"(.*)\(\) got an unexpected keyword argument '(.*)'", x.args[0])
                if m:
                    fname, pname = m.groups()
                    msg = ("The '%s' page handler received a '%s' parameter, "
                           "which it does not handle." % (fname, pname))
                    raise TypeError(msg, repr(func))
            cherrypy.response.body = iterable(body)
            return
        except cherrypy.InternalRedirect, x:
            # Try again with the new path
            path = x.path

def iterable(body):
    """Convert the given body to an iterable object."""
    if isinstance(body, types.FileType):
        body = fileGenerator(body)
    elif isinstance(body, types.GeneratorType):
        body = flattener(body)
    elif isinstance(body, basestring):
        body = [body]
    elif body is None:
        body = [""]
    return body

def checkStatus():
    """Test/set cherrypy.response.status. Provide Reason-phrase if missing."""
    if not cherrypy.response.status:
        cherrypy.response.status = "200 OK"
    else:
        status = str(cherrypy.response.status)
        parts = status.split(" ", 1)
        if len(parts) == 1:
            # No reason supplied.
            code, = parts
            reason = None
        else:
            code, reason = parts
            reason = reason.strip()
        
        try:
            code = int(code)
            assert code >= 100 and code < 600
        except (ValueError, AssertionError):
            code = 500
            reason = None
        
        if reason is None:
            try:
                reason = responseCodes[code][0]
            except (KeyError, IndexError):
                reason = ""
        
        cherrypy.response.status = "%s %s" % (code, reason)
    return cherrypy.response.status


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


def finalize():
    """Transform headerMap (and cookies) into cherrypy.response.headers."""
    
    checkStatus()
    
    if cherrypy.response.body is None:
        cherrypy.response.body = []
    
    if cherrypy.response.headerMap.get('Content-Length') is None:
        if (cherrypy.request.version < "1.1" or
            # OPTIONS requests MUST include a Content-Length of 0 if no body.
            # Just punt and figure len for all OPTIONS requests.
            cherrypy.request.method == "OPTIONS"):
            
            content = ''.join([chunk for chunk in cherrypy.response.body])
            cherrypy.response.body = [content]
            cherrypy.response.headerMap['Content-Length'] = len(content)
        else:
            try:
                del cherrypy.response.headerMap['Content-Length']
            except KeyError:
                pass
    
    # For some statuses, Internet Explorer 5+ shows "friendly error messages"
    # instead of our response.body if the body is smaller than a given size.
    # Fix this by returning a body over that size (by adding whitespace).
    # See http://support.microsoft.com/kb/q218155/
    s = int(cherrypy.response.status.split(" ")[0])
    s = _ie_friendly_error_sizes.get(s, 0)
    if s:
        s += 1
        # Since we are issuing an HTTP error status, we assume that
        # the entity is short, and we should just collapse it.
        content = ''.join([chunk for chunk in cherrypy.response.body])
        cherrypy.response.body = [content]
        l = len(content)
        if l and l < s:
            # IN ADDITION: the response must be written to IE
            # in one chunk or it will still get replaced! Bah.
            cherrypy.response.body = [cherrypy.response.body[0] + (" " * (s - l))]
            cherrypy.response.headerMap['Content-Length'] = s
    
    # Headers
    headers = []
    for key, valueList in cherrypy.response.headerMap.iteritems():
        order = _header_order_map.get(key, 3)
        if not isinstance(valueList, list):
            valueList = [valueList]
        for value in valueList:
            headers.append((order, (key, str(value))))
    # RFC 2616: '... it is "good practice" to send general-header fields
    # first, followed by request-header or response-header fields, and
    # ending with the entity-header fields.'
    headers.sort()
    cherrypy.response.headers = [item[1] for item in headers]
    
    cookie = cherrypy.response.simpleCookie.output()
    if cookie:
        lines = cookie.split("\n")
        for line in lines:
            name, value = line.split(": ", 1)
            cherrypy.response.headers.append((name, value))


def applyFilters(methodName):
    """Execute the given method for all registered filters."""
    if methodName in ('beforeRequestBody', 'beforeMain'):
        filterList = (_cputil._cpDefaultInputFilterList +
                      _cputil.getSpecialAttribute('_cpFilterList'))
    elif methodName in ('beforeFinalize',):
        filterList = (_cputil.getSpecialAttribute('_cpFilterList') +
                      _cputil._cpDefaultOutputFilterList)
    else:
        # 'onStartResource', 'onEndResource'
        # 'beforeErrorResponse', 'afterErrorResponse'
        filterList = (_cputil._cpDefaultInputFilterList +
                      _cputil.getSpecialAttribute('_cpFilterList') +
                      _cputil._cpDefaultOutputFilterList)
    for filter in filterList:
        method = getattr(filter, methodName, None)
        if method:
            method()

def fileGenerator(input, chunkSize=65536):
    """Yield the given input (a file object) in chunks (default 64k)."""
    chunk = input.read(chunkSize)
    while chunk:
        yield chunk
        chunk = input.read(chunkSize)
    input.close()

def flattener(input):
    """Yield the given input, recursively iterating over each result (if needed)."""
    for x in input:
        if not isinstance(x, types.GeneratorType):
            yield x
        else:
            for y in flattener(x):
                yield y 


def get_ranges(content_length):
    """Return a list of (start, stop) indices from a Range header, or None.
    
    Each (start, stop) tuple will be composed of two ints, which are suitable
    for use in a slicing operation. That is, the header "Range: bytes=3-6",
    if applied against a Python string, is requesting resource[3:7]. This
    function will return the list [(3, 7)].
    """
    
    r = cherrypy.request.headerMap.get('Range')
    if not r:
        return None
    
    result = []
    bytesunit, byteranges = r.split("=", 1)
    for brange in byteranges.split(","):
        start, stop = [x.strip() for x in brange.split("-", 1)]
        if start:
            if not stop:
                stop = content_length - 1
            start, stop = map(int, (start, stop))
            if start >= content_length:
                # From rfc 2616 sec 14.16:
                # "If the server receives a request (other than one
                # including an If-Range request-header field) with an
                # unsatisfiable Range request-header field (that is,
                # all of whose byte-range-spec values have a first-byte-pos
                # value greater than the current length of the selected
                # resource), it SHOULD return a response code of 416
                # (Requested range not satisfiable)."
                continue
            if stop < start:
                # From rfc 2616 sec 14.16:
                # "If the server ignores a byte-range-spec because it
                # is syntactically invalid, the server SHOULD treat
                # the request as if the invalid Range header field
                # did not exist. (Normally, this means return a 200
                # response containing the full entity)."
                return None
            result.append((start, stop + 1))
        else:
            if not stop:
                # See rfc quote above.
                return None
            # Negative subscript (last N bytes)
            result.append((content_length - int(stop), content_length))
    
    if result == []:
        cherrypy.response.headerMap['Content-Range'] = "bytes */%s" % content_length
        b = "Invalid Range (first-byte-pos greater than Content-Length)"
        raise cherrypy.HTTPClientError(416, b)
    
    return result


def serve_file(filename):
    """Set status, headers, and body in order to serve the given file."""
    
    # If filename is relative, make absolute using cherrypy.root's module.
    if not os.path.isabs(filename):
        root = os.path.dirname(sys.modules[cherrypy.root.__module__].__file__)
        filename = os.path.join(root, filename)
    
    # Serve filename
    try:
        stat = os.stat(filename)
    except OSError:
        if getattr(cherrypy, "debug", None):
            cherrypy.log("    NOT FOUND file: %s" % filename, "DEBUG")
        raise cherrypy.NotFound(cherrypy.request.path)
    
    # Set content-type based on filename extension
    i = filename.rfind('.')
    if i != -1:
        ext = filename[i:]
    else:
        ext = ""
    
    resp = cherrypy.response
    
    contentType = mimetypes.types_map.get(ext, "text/plain")
    resp.headerMap['Content-Type'] = contentType
    
    strModifTime = httpdate(time.gmtime(stat.st_mtime))
    if cherrypy.request.headerMap.has_key('If-Modified-Since'):
        # Check if if-modified-since date is the same as strModifTime
        if cherrypy.request.headerMap['If-Modified-Since'] == strModifTime:
            resp.status = "304 Not Modified"
            resp.body = []
            if getattr(cherrypy, "debug", None):
                cherrypy.log("    Found file (304 Not Modified): %s" % filename, "DEBUG")
            return
    resp.headerMap['Last-Modified'] = strModifTime
    
    # Set Content-Length and use an iterable (file object)
    #   this way CP won't load the whole file in memory
    c_len = stat[6]
    bodyfile = open(filename, 'rb')
    if getattr(cherrypy, "debug", None):
        cherrypy.log("    Found file: %s" % filename, "DEBUG")
    
    resp.headerMap["Accept-Ranges"] = "bytes"
    r = get_ranges(c_len)
    if r:
        if len(r) == 1:
            # Return a single-part response.
            start, stop = r[0]
            r_len = stop - start
            resp.status = "206 Partial Content"
            resp.headerMap['Content-Range'] = ("bytes %s-%s/%s" %
                                               (start, stop - 1, c_len))
            resp.headerMap['Content-Length'] = r_len
            bodyfile.seek(start)
            resp.body = [bodyfile.read(r_len)]
        else:
            # Return a multipart/byteranges response.
            resp.status = "206 Partial Content"
            import mimetools
            boundary = mimetools.choose_boundary()
            resp.headerMap['Content-Type'] = "multipart/byteranges; boundary=%s" % boundary
            del resp.headerMap['Content-Length']
            def fileRanges():
                for start, stop in r:
                    yield "--" + boundary
                    yield "\nContent-type: %s" % contentType
                    yield ("\nContent-range: bytes %s-%s/%s\n\n"
                           % (start, stop - 1, c_len))
                    bodyfile.seek(start)
                    yield bodyfile.read((stop + 1) - start)
                    yield "\n"
                # Final boundary
                yield "--" + boundary
            resp.body = fileRanges()
    else:
        resp.headerMap['Content-Length'] = c_len
        resp.body = fileGenerator(bodyfile)


# Object lookup

def getObjFromPath(objPathList):
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

def mapPathToObject(path):
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
    tpath = path.strip("/")
    
    if not tpath:
        objectPathList = []
    else:
        objectPathList = tpath.split('/')
    if objectPathList == ['global']:
        objectPathList = ['_global']
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
            candidate = getObjFromPath(objectPathList)
            if callable(candidate) and getattr(candidate, 'exposed', False):
                foundIt = True
                break
        # Couldn't find the object: pop one from the list and try "default"
        lastObj = objectPathList.pop()
        if (not isFirst) or (not tpath):
            virtualPathList.insert(0, lastObj)
            objectPathList.append('default')
            candidate = getObjFromPath(objectPathList)
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
            serve_file(icofile)
            finalize()
            raise cherrypy.RequestHandled()
        else:
            # We didn't find anything
            if getattr(cherrypy, "debug", None):
                cherrypy.log("    NOT FOUND", "DEBUG")
            raise cherrypy.NotFound(path)
    
    if isFirst:
        # We found the extra ".index"
        # Check if the original path had a trailing slash (otherwise, do
        #   a redirect)
        if path[-1] != '/':
            newUrl = path + '/'
            if cherrypy.request.queryString:
                newUrl += "?" + cherrypy.request.queryString
            if getattr(cherrypy, "debug", None):
                cherrypy.log("    Found: redirecting to %s" % newUrl, "DEBUG")
            raise cherrypy.HTTPRedirect(newUrl)
    
    if getattr(cherrypy, "debug", None):
        cherrypy.log("    Found: %s" % candidate, "DEBUG")
    return candidate, objectPathList, virtualPathList

