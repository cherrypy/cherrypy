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

import cgi

import Cookie
import os
import re
import sys
import types
import urllib
from urlparse import urlparse

import cherrypy
from cherrypy import _cputil, _cpcgifs, _cpwsgiserver, _cperror
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


class KeyTitlingDict(dict):
    
    """A dict subclass which changes each key to str(key).title()
    
    This allows headers to be case-insensitive and avoid duplicates.
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
    
    def setdefault(self, key, x=None):
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
        
        clientAddress should be a tuple of client IP address, client Port
        remoteHost should be string of the client's IP address.
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
        
        request = cherrypy.request
        request.method = ""
        request.requestLine = requestLine.strip()
        self.parseFirstLine()
        
        self.requestHeaders = headers
        
        # Prepare cherrypy.request variables
        request.remoteAddr = clientAddress[0]
        request.remotePort = clientAddress[1]
        request.remoteHost = remoteHost
        request.paramList = [] # Only used for Xml-Rpc
        request.headerMap = KeyTitlingDict()
        request.simpleCookie = Cookie.SimpleCookie()
        request.rfile = rfile
        request.scheme = scheme
        
        # Prepare cherrypy.response variables
        cherrypy.response.status = None
        cherrypy.response.headers = None
        cherrypy.response.body = None
        
        cherrypy.response.headerMap = KeyTitlingDict()
        cherrypy.response.headerMap.update({
            "Content-Type": "text/html",
            "Server": "CherryPy/" + cherrypy.__version__,
            "Date": cptools.HTTPDate(),
            "Set-Cookie": [],
            "Content-Length": None
        })
        cherrypy.response.simpleCookie = Cookie.SimpleCookie()
        
        self.run()
        
        if request.method == "HEAD":
            # HEAD requests MUST NOT return a message-body in the response.
            cherrypy.response.body = []
        
        _cputil.getSpecialAttribute("_cpLogAccess")()
    
    def parseFirstLine(self):
        # This has to be done very early in the request process,
        # because request.path is used for config lookups right away.
        request = cherrypy.request
        
        # Parse first line
        request.method, path, request.protocol = request.requestLine.split()
        request.processRequestBody = request.method in ("POST", "PUT")
        
        # separate the queryString, or set it to "" if not found
        if "?" in path:
            path, request.queryString = path.split("?", 1)
        else:
            path, request.queryString = path, ""
        
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
        request.path = request.originalPath = path
        
        # Change objectPath in filters to change
        # the object that will get rendered
        request.objectPath = None
    
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
                except (cherrypy.HTTPRedirect, cherrypy.HTTPError), inst:
                    # For an HTTPRedirect or HTTPError (including NotFound),
                    # we don't go through the regular mechanism:
                    # we return the redirect or error page immediately
                    inst.set_response()
                    applyFilters('beforeFinalize')
                    finalize()
            finally:
                applyFilters('onEndResource')
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            handleError(sys.exc_info())
    
    def processRequestHeaders(self):
        request = cherrypy.request
        
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
        request_v = Version.from_http(request.protocol)
        server_v = cherrypy.config.get("server.protocolVersion", "HTTP/1.0")
        server_v = Version.from_http(server_v)
        # cherrypy.response.version should be used to determine whether or
        # not to include a given HTTP/1.1 feature in the response content.
        cherrypy.response.version = min(request_v, server_v)
        # cherrypy.request.version == request.protocol in a Version instance.
        cherrypy.request.version = request_v
        
        # build a paramMap dictionary from queryString
        if re.match(r"[0-9]+,[0-9]+", request.queryString):
            # Server-side image map. Map the coords to 'x' and 'y'
            # (like CGI::Request does).
            pm = request.queryString.split(",")
            pm = {'x': int(pm[0]), 'y': int(pm[1])}
        else:
            pm = cgi.parse_qs(request.queryString, keep_blank_values=True)
            for key, val in pm.items():
                if len(val) == 1:
                    pm[key] = val[0]
        request.paramMap = pm
        
        # Process the headers into request.headerMap
        for name, value in self.requestHeaders:
            value = value.strip()
            # Warning: if there is more than one header entry for cookies (AFAIK,
            # only Konqueror does that), only the last one will remain in headerMap
            # (but they will be correctly stored in request.simpleCookie).
            request.headerMap[name] = value
            
            # Handle cookies differently because on Konqueror, multiple
            # cookies come on different lines with the same key
            if name.title() == 'Cookie':
                request.simpleCookie.load(value)
        
        # Write a message to the error.log only if there is no access.log.
        # This is only here for backwards-compatibility (with the time
        # before the access.log existed), and should be removed in CP 2.2.
        fname = cherrypy.config.get('server.logAccessFile', '')
        if not fname:
            msg = "%s - %s" % (request.remoteAddr, request.requestLine)
            cherrypy.log(msg, "HTTP")
        
        # Save original values (in case they get modified by filters)
        request.originalParamMap = request.paramMap
        request.originalParamList = request.paramList
        
        if cherrypy.response.version >= "1.1":
            # All Internet-based HTTP/1.1 servers MUST respond with a 400
            # (Bad Request) status code to any HTTP/1.1 request message
            # which lacks a Host header field.
            if not request.headerMap.has_key("Host"):
                cherrypy.response.status = 400
                cherrypy.response.body = ["HTTP/1.1 requires a 'Host' request header."]
                finalize()
                raise cherrypy.RequestHandled()
        request.base = "%s://%s" % (request.scheme, request.headerMap.get('Host', ''))
        request.browserUrl = request.base + request.path
    
    def processRequestBody(self):
        request = cherrypy.request
        
        # Create a copy of headerMap with lowercase keys because
        # FieldStorage doesn't work otherwise
        lowerHeaderMap = {}
        for key, value in request.headerMap.items():
            lowerHeaderMap[key.lower()] = value
        
        # FieldStorage only recognizes POST, so fake it.
        methenv = {'REQUEST_METHOD': "POST"}
        try:
            forms = _cpcgifs.FieldStorage(fp=request.rfile,
                                      headers=lowerHeaderMap,
                                      environ=methenv,
                                      keep_blank_values=1)
        except _cpwsgiserver.MaxSizeExceeded:
            # Post data is too big
            raise _cperror.HTTPError(413)
        
        if forms.file:
            # request body was a content-type other than form params.
            cherrypy.request.body = forms.file
        else:
            for key in forms.keys():
                valueList = forms[key]
                if isinstance(valueList, list):
                    request.paramMap[key] = []
                    for item in valueList:
                        if item.filename is not None:
                            value = item # It's a file upload
                        else:
                            value = item.value # It's a regular field
                        request.paramMap[key].append(value)
                else:
                    if valueList.filename is not None:
                        value = valueList # It's a file upload
                    else:
                        value = valueList.value # It's a regular field
                    request.paramMap[key] = value


# Error handling

dbltrace = """
=====First Error=====

%s

=====Second Error=====

%s

"""

def handleError(exc):
    """Set status, headers, and body when an unanticipated error occurs."""
    try:
        applyFilters('beforeErrorResponse')
       
        # _cpOnError will probably change cherrypy.response.body.
        # It may also change the headerMap, etc.
        _cputil.getSpecialAttribute('_cpOnError')()
        
        finalize()
        
        applyFilters('afterErrorResponse')
        return
    except (cherrypy.HTTPRedirect, cherrypy.HTTPError), inst:
        try:
            inst.set_response()
            finalize()
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
    defaultOn = (cherrypy.config.get('server.environment') == 'development')
    if cherrypy.config.get('server.showTracebacks', defaultOn):
        body = dbltrace % (_cputil.formatExc(exc), _cputil.formatExc())
    else:
        body = ""
    response = cherrypy.response
    response.status, response.headers, response.body = bareError(body)

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



# Response functions

def main(path=None):
    """Obtain and set cherrypy.response.body from a page handler."""
    if path is None:
        path = cherrypy.request.objectPath or cherrypy.request.path
    
    while True:
        try:
            page_handler, object_path, virtual_path = mapPathToObject(path)
            
            # Remove "root" from object_path and join it to get objectPath
            cherrypy.request.objectPath = '/' + '/'.join(object_path[1:])
            args = virtual_path + cherrypy.request.paramList
            body = page_handler(*args, **cherrypy.request.paramMap)
            cherrypy.response.body = iterable(body)
            return
        except cherrypy.InternalRedirect, x:
            # Try again with the new path
            path = x.path

def iterable(body):
    """Convert the given body to an iterable object."""
    if isinstance(body, types.FileType):
        body = cptools.fileGenerator(body)
    elif isinstance(body, types.GeneratorType):
        body = flattener(body)
    elif isinstance(body, basestring):
        body = [body]
    elif body is None:
        body = [""]
    return body


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
    
    response = cherrypy.response
    
    code, reason, _ = cptools.validStatus(response.status)
    response.status = "%s %s" % (code, reason)
    
    if response.body is None:
        response.body = []
    
    stream = cherrypy.config.get("streamResponse", False)
    # OPTIONS requests MUST include a Content-Length of 0 if no body.
    # Just punt and figure Content-Length for all OPTIONS requests.
    if cherrypy.request.method == "OPTIONS":
        stream = False
    
    if stream:
        try:
            del response.headerMap['Content-Length']
        except KeyError:
            pass
    else:
        # Responses which are not streamed should have a Content-Length,
        # but allow user code to set Content-Length if desired.
        if response.headerMap.get('Content-Length') is None:
            content = ''.join([chunk for chunk in response.body])
            response.body = [content]
            response.headerMap['Content-Length'] = len(content)
    
    # For some statuses, Internet Explorer 5+ shows "friendly error messages"
    # instead of our response.body if the body is smaller than a given size.
    # Fix this by returning a body over that size (by adding whitespace).
    # See http://support.microsoft.com/kb/q218155/
    s = int(response.status.split(" ")[0])
    s = _ie_friendly_error_sizes.get(s, 0)
    if s:
        s += 1
        # Since we are issuing an HTTP error status, we assume that
        # the entity is short, and we should just collapse it.
        content = ''.join([chunk for chunk in response.body])
        response.body = [content]
        l = len(content)
        if l and l < s:
            # IN ADDITION: the response must be written to IE
            # in one chunk or it will still get replaced! Bah.
            response.body = [response.body[0] + (" " * (s - l))]
            response.headerMap['Content-Length'] = s
    
    # Headers
    headers = []
    for key, valueList in response.headerMap.iteritems():
        order = _header_order_map.get(key, 3)
        if not isinstance(valueList, list):
            valueList = [valueList]
        for value in valueList:
            headers.append((order, (key, str(value))))
    # RFC 2616: '... it is "good practice" to send general-header fields
    # first, followed by request-header or response-header fields, and
    # ending with the entity-header fields.'
    headers.sort()
    response.headers = [item[1] for item in headers]
    
    cookie = response.simpleCookie.output()
    if cookie:
        lines = cookie.split("\n")
        for line in lines:
            name, value = line.split(": ", 1)
            response.headers.append((name, value))


def applyFilters(methodName):
    """Execute the given method for all registered filters."""
    if methodName in ('onStartResource', 'beforeRequestBody', 'beforeMain'):
        filterList = (_cputil._cpDefaultInputFilterList +
                      _cputil.getSpecialAttribute('_cpFilterList'))
    elif methodName in ('beforeFinalize', 'onEndResource',
                'beforeErrorResponse', 'afterErrorResponse'):
        filterList = (_cputil.getSpecialAttribute('_cpFilterList') +
                      _cputil._cpDefaultOutputFilterList)
    #else:
    #    # '', 
    #    # 'beforeErrorResponse', 'afterErrorResponse'
    #    filterList = (_cputil._cpDefaultInputFilterList +
    #                  _cputil.getSpecialAttribute('_cpFilterList') +
    #                  _cputil._cpDefaultOutputFilterList)
    else:
        assert False # Wrong methodName for the filter
    for filter in filterList:
        method = getattr(filter, methodName, None)
        if method:
            method()

def flattener(input):
    """Yield the given input, recursively iterating over each result (if needed)."""
    for x in input:
        if not isinstance(x, types.GeneratorType):
            yield x
        else:
            for y in flattener(x):
                yield y 


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
            cptools.serveFile(icofile)
            applyFilters('beforeFinalize')
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

