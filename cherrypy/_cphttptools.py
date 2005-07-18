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

import urllib, os, sys, time, types, cgi
import mimetypes, Cookie

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
    """httpdate(dt=None) -> the given time.struct_time in RFC 1123 format.
    
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


class KeyTitlingDict(dict):
    """dict subclass which changes each key to str(key).title()
    
    This should allow response headers to be case-insensitive and
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
    """Process a request and yield a series of response chunks.
    
    headers should be a list of (name, value) tuples.
    """
    
    def __init__(self, clientAddress, remoteHost, requestLine, headers,
                 rfile, scheme="http"):
        # When __init__ is finished, cherrypy.response should have three attributes:
        #   status, e.g. "200 OK"
        #   headers, a list of (name, value) tuples
        #   body, an iterable yielding strings
        # Consumer code should then access these three attributes
        # to build the outbound stream.
        
        self.requestLine = requestLine
        self.requestHeaders = headers
        
        # Prepare cherrypy.request variables
        cherrypy.request.remoteAddr = clientAddress
        cherrypy.request.remoteHost = remoteHost
        cherrypy.request.paramList = [] # Only used for Xml-Rpc
        cherrypy.request.headerMap = {}
        cherrypy.request.requestLine = requestLine
        cherrypy.request.simpleCookie = Cookie.SimpleCookie()
        cherrypy.request.rfile = rfile
        cherrypy.request.scheme = scheme
        cherrypy.request.method = ""
        
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
            "Content-Length": 0
        })
        cherrypy.response.simpleCookie = Cookie.SimpleCookie()
        
        self.run()
        
        if cherrypy.request.method == "HEAD":
            # HEAD requests MUST NOT return a message-body in the response.
            cherrypy.response.body = []
    
    def run(self):
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
            handleError(sys.exc_info())
    
    def processRequestHeaders(self):
        req = cherrypy.request
        
        # Parse first line
        req.method, path, req.protocol = self.requestLine.split()
        req.processRequestBody = req.method in ("POST", "PUT")
        
        # find the queryString, or set it to "" if not found
        if "?" in path:
            req.path, req.queryString = path.split("?", 1)
        else:
            req.path, req.queryString = path, ""
        
        # build a paramMap dictionary from queryString
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
        
        msg = "%s - %s" % (req.remoteAddr, self.requestLine.strip())
        cherrypy.log(msg, "HTTP")
        
        req.base = "%s://%s" % (req.scheme, req.headerMap.get('Host', ''))
        req.browserUrl = req.base + path
        
        # Change objectPath in filters to change
        # the object that will get rendered
        req.objectPath = None
        
        # Save original values (in case they get modified by filters)
        req.originalPath = req.path
        req.originalParamMap = req.paramMap
        req.originalParamList = req.paramList
    
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
        body = dbltrace % (_cputil.formatExc(exc), _cputil.formatExc())
        cherrypy.response.status, cherrypy.response.headers, body = bareError(body)
        cherrypy.response.body = body

def bareError(extrabody=None):
    """bareError(extrabody=None) -> status, headers, body.
    
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
    """Obtain and set cherrypy.response.body."""
    if path is None:
        path = cherrypy.request.objectPath or cherrypy.request.path
    
    while True:
        try:
            func, objectPathList, virtualPathList = mapPathToObject(path)
            
            # Remove "root" from objectPathList and join it to get objectPath
            cherrypy.request.objectPath = '/' + '/'.join(objectPathList[1:])
            body = func(*(virtualPathList + cherrypy.request.paramList),
                        **(cherrypy.request.paramMap))
            cherrypy.response.body = iterable(body)
            return
        except cherrypy.InternalRedirect, x:
            # Try again with the new path
            path = x.path

def iterable(body):
    # build a uniform return type (iterable)
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


def finalize():
    """Transform headerMap + cookies into cherrypy.response.headers."""
    
    checkStatus()
    
    if cherrypy.response.body is None:
        cherrypy.response.body = []
    
    if (cherrypy.config.get("server.protocolVersion") != "HTTP/1.1"
        and cherrypy.response.headerMap.get('Content-Length') == 0):
        content = ''.join([chunk for chunk in cherrypy.response.body])
        cherrypy.response.body = [content]
        cherrypy.response.headerMap['Content-Length'] = len(content)
    
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
    
    return cherrypy.response.headers

def applyFilters(methodName):
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
    # Iterate over the file in 64k chunks
    chunk = input.read(chunkSize)
    while chunk:
        yield chunk
        chunk = input.read(chunkSize)
    input.close()

def flattener(input):
    for x in input:
        if not isinstance(x, types.GeneratorType):
            yield x
        else:
            for y in flattener(x):
                yield y 


def serve_file(filename):
    # If filename is relative, make absolute using cherrypy.root's module.
    if not os.path.isabs(filename):
        root = os.path.dirname(sys.modules[cherrypy.root.__module__].__file__)
        filename = os.path.join(root, filename)
    
    # Serve filename
    try:
        stat = os.stat(filename)
    except OSError:
        raise cherrypy.NotFound(cherrypy.request.path)

    # Set content-type based on filename extension
    i = filename.rfind('.')
    if i != -1:
        ext = filename[i:]
    else:
        ext = ""
        
    contentType = mimetypes.types_map.get(ext, "text/plain")
    cherrypy.response.headerMap['Content-Type'] = contentType
    
    strModifTime = httpdate(time.gmtime(stat.st_mtime))
    if cherrypy.request.headerMap.has_key('If-Modified-Since'):
        # Check if if-modified-since date is the same as strModifTime
        if cherrypy.request.headerMap['If-Modified-Since'] == strModifTime:
            cherrypy.response.status = "304 Not Modified"
            cherrypy.response.body = []
            return
    cherrypy.response.headerMap['Last-Modified'] = strModifTime
    
    # Set Content-Length and use an iterable (file object)
    #   this way CP won't load the whole file in memory
    cherrypy.response.headerMap['Content-Length'] = stat[6]
    bodyfile = open(filename, 'rb')
    cherrypy.response.body = fileGenerator(bodyfile)
    
    


# Object lookup

def getObjFromPath(objPathList):
    """ For a given objectPathList (like ['root', 'a', 'b', 'index']),
         return the object (or None if it doesn't exist).
    """
    root = cherrypy
    for objname in objPathList:
        # maps virtual filenames to Python identifiers (substitutes '.' for '_')
        objname = objname.replace('.', '_')
        if getattr(cherrypy, "debug", None):
            print "Attempting to call method: %s.%s" % (root, objname)
        root = getattr(root, objname, None)
        if root is None:
            return None
    return root

def mapPathToObject(path):
    # Traverse path:
    # for /a/b?arg=val, we'll try:
    #   root.a.b.index -> redirect to /a/b/?arg=val
    #   root.a.b.default(arg='val') -> redirect to /a/b/?arg=val
    #   root.a.b(arg='val')
    #   root.a.default('b', arg='val')
    #   root.default('a', 'b', arg='val')
    
    # Also, we ignore trailing slashes
    # Also, a method has to have ".exposed = True" in order to be exposed
    # Remove leading and trailing slash
    tpath = path.strip("/")
    # Replace quoted chars (eg %20) from url
    tpath = urllib.unquote(tpath)
    
    if not tpath:
        objectPathList = []
    else:
        objectPathList = tpath.split('/')
    objectPathList = ['root'] + objectPathList + ['index']
    
    if getattr(cherrypy, "debug", None):
        print "Attempting to map path: %s" % tpath
        print "    objectPathList: %s" % objectPathList
    
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
            raise cherrypy.RequestHandled
        else:
            # We didn't find anything
            raise cherrypy.NotFound(path)
    
    if isFirst:
        # We found the extra ".index"
        # Check if the original path had a trailing slash (otherwise, do
        #   a redirect)
        if path[-1] != '/':
            newUrl = path + '/'
            if cherrypy.request.queryString:
                newUrl += "?" + cherrypy.request.queryString
            raise cherrypy.HTTPRedirect(newUrl)
    
    return candidate, objectPathList, virtualPathList

