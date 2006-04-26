"""CherryPy core request/response handling."""

import Cookie
import os
import sys
import types

import cherrypy
from cherrypy import _cputil, _cpcgifs, tools
from cherrypy.lib import cptools, httptools


class Request(object):
    """An HTTP request."""
    
    def __init__(self, remote_addr, remote_port, remote_host, scheme="http"):
        """Populate a new Request object.
        
        remote_addr should be the client IP address
        remote_port should be the client Port
        remote_host should be string of the client's IP address.
        scheme should be a string, either "http" or "https".
        """
        self.remote_addr  = remote_addr
        self.remote_port  = remote_port
        self.remote_host  = remote_host
        
        self.scheme = scheme
        self.closed = False
        
        pts = ['on_start_resource', 'before_request_body',
               'before_main', 'before_finalize',
               'on_end_resource', 'on_end_request',
               'before_error_response', 'after_error_response']
        self.hooks = tools.HookMap(pts)
        self.hooks.failsafe = ['on_start_resource', 'on_end_resource',
                               'on_end_request']
    
    def close(self):
        if not self.closed:
            self.closed = True
            self.hooks.run('on_end_request')
            cherrypy.serving.__dict__.clear()
    
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
        self.requestLine = requestLine.strip()
        self.header_list = list(headers)
        self.rfile = rfile
        
        self.headers = httptools.HeaderMap()
        self.simple_cookie = Cookie.SimpleCookie()
        
        if cherrypy.profiler:
            cherrypy.profiler.run(self._run)
        else:
            self._run()
        
        if self.method == "HEAD":
            # HEAD requests MUST NOT return a message-body in the response.
            cherrypy.response.body = []
        
        _cputil.get_special_attribute("_cp_log_access")()
        
        return cherrypy.response
    
    def _run(self):
        
        try:
            # This has to be done very early in the request process,
            # because request.object_path is used for config lookups
            # right away.
            self.processRequestLine()
            self.dispatch = cherrypy.config.get("dispatch") or dispatch
            self.hooks.setup()
            
            try:
                self.hooks.run('on_start_resource')
                
                try:
                    self.processHeaders()
                    
                    self.hooks.run('before_request_body')
                    if self.processRequestBody:
                        self.processBody()
                    
                    # Loop to allow for InternalRedirect.
                    while True:
                        try:
                            self.hooks.run('before_main')
                            if self.dispatch:
                                self.dispatch(self.object_path)
                            break
                        except cherrypy.InternalRedirect, ir:
                            self.object_path = ir.path
                    
                    self.hooks.run('before_finalize')
                    cherrypy.response.finalize()
                except cherrypy.RequestHandled:
                    pass
                except (cherrypy.HTTPRedirect, cherrypy.HTTPError), inst:
                    # For an HTTPRedirect or HTTPError (including NotFound),
                    # we don't go through the regular mechanism:
                    # we return the redirect or error page immediately
                    inst.set_response()
                    self.hooks.run('before_finalize')
                    cherrypy.response.finalize()
            finally:
                self.hooks.run('on_end_resource')
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            if cherrypy.config.get("server.throw_errors", False):
                raise
            cherrypy.response.handleError(sys.exc_info())
    
    def processRequestLine(self):
        rl = self.requestLine
        method, path, qs, proto = httptools.parseRequestLine(rl)
        if path == "*":
            path = "global"
        
        self.method = method
        self.processRequestBody = method in ("POST", "PUT")
        
        self.path = path
        self.query_string = qs
        self.protocol = proto
        
        # Change object_path to change the object that will get rendered
        self.object_path = path
        
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
        
        # cherrypy.response.version should be used to determine whether or
        # not to include a given HTTP/1.1 feature in the response content.
        server_v = cherrypy.config.get("server.protocol_version", "HTTP/1.0")
        server_v = httptools.Version.from_http(server_v)
        cherrypy.response.version = min(self.version, server_v)
    
    def processHeaders(self):
        self.params = httptools.parseQueryString(self.query_string)
        
        # Process the headers into self.headers
        for name, value in self.header_list:
            value = value.strip()
            # Warning: if there is more than one header entry for cookies (AFAIK,
            # only Konqueror does that), only the last one will remain in headers
            # (but they will be correctly stored in request.simple_cookie).
            self.headers[name] = value
            
            # Handle cookies differently because on Konqueror, multiple
            # cookies come on different lines with the same key
            if name.title() == 'Cookie':
                self.simple_cookie.load(value)
        
        if self.version >= "1.1":
            # All Internet-based HTTP/1.1 servers MUST respond with a 400
            # (Bad Request) status code to any HTTP/1.1 request message
            # which lacks a Host header field.
            if not self.headers.has_key("Host"):
                msg = "HTTP/1.1 requires a 'Host' request header."
                raise cherrypy.HTTPError(400, msg)
        self.base = "%s://%s" % (self.scheme, self.headers.get('Host', ''))
    
    def _get_browser_url(self):
        url = self.base + self.path
        if self.query_string:
            url += '?' + self.query_string
        return url
    browser_url = property(_get_browser_url,
                          doc="The URL as entered in a browser (read-only).")
    
    def processBody(self):
        # Create a copy of headers with lowercase keys because
        # FieldStorage doesn't work otherwise
        lowerHeaderMap = {}
        for key, value in self.headers.items():
            lowerHeaderMap[key.lower()] = value
        
        # FieldStorage only recognizes POST, so fake it.
        methenv = {'REQUEST_METHOD': "POST"}
        try:
            forms = _cpcgifs.FieldStorage(fp=self.rfile,
                                          headers=lowerHeaderMap,
                                          environ=methenv,
                                          keep_blank_values=1)
        except httptools.MaxSizeExceeded:
            # Post data is too big
            raise cherrypy.HTTPError(413)
        
        if forms.file:
            # request body was a content-type other than form params.
            self.body = forms.file
        else:
            self.params.update(httptools.paramsFromCGIForm(forms))


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

def find_handler(objectpath):
    """Find the appropriate page handler for the given path."""
    objectTrail = _cputil.get_object_trail(objectpath)
    names = [name for name, candidate in objectTrail]
    
    # Try successive objects (reverse order)
    mounted_app_roots = cherrypy.tree.mount_points.values()
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
                    atoms = cherrypy.request.browser_url.split("?", 1)
                    newUrl = atoms.pop(0) + '/'
                    if atoms:
                        newUrl += "?" + atoms[0]
                    raise cherrypy.HTTPRedirect(newUrl)
            return candidate, names[:i+1], names[i+1:-1]
        
        if candidate in mounted_app_roots:
            break
    
    # We didn't find anything
    raise cherrypy.NotFound(objectpath)


class Body(object):
    """The body of the HTTP response (the response entity)."""
    
    def __get__(self, obj, objclass=None):
        if obj is None:
            # When calling on the class instead of an instance...
            return self
        else:
            return obj._body
    
    def __set__(self, obj, value):
        # Convert the given value to an iterable object.
        if isinstance(value, types.FileType):
            value = cptools.fileGenerator(value)
        elif isinstance(value, types.GeneratorType):
            value = flattener(value)
        elif isinstance(value, basestring):
            # strings get wrapped in a list because iterating over a single
            # item list is much faster than iterating over every character
            # in a long string.
            value = [value]
        elif value is None:
            value = []
        obj._body = value


def flattener(input):
    """Yield the given input, recursively iterating over each result (if needed)."""
    for x in input:
        if not isinstance(x, types.GeneratorType):
            yield x
        else:
            for y in flattener(x):
                yield y 


class Response(object):
    """An HTTP Response."""
    
    body = Body()
    
    def __init__(self):
        self.status = None
        self.header_list = None
        self.body = None
        
        self.headers = httptools.HeaderMap()
        content_type = cherrypy.config.get('server.default_content_type', 'text/html')
        self.headers.update({
            "Content-Type": content_type,
            "Server": "CherryPy/" + cherrypy.__version__,
            "Date": httptools.HTTPDate(),
            "Set-Cookie": [],
            "Content-Length": None
        })
        self.simple_cookie = Cookie.SimpleCookie()
    
    def collapse_body(self):
        newbody = ''.join([chunk for chunk in self.body])
        self.body = newbody
        return newbody
    
    def finalize(self):
        """Transform headers (and cookies) into cherrypy.response.header_list."""
        
        try:
            code, reason, _ = httptools.validStatus(self.status)
        except ValueError, x:
            raise cherrypy.HTTPError(500, x.args[0])
        
        self.status = "%s %s" % (code, reason)
        
        stream = cherrypy.config.get("stream_response", False)
        # OPTIONS requests MUST include a Content-Length of 0 if no body.
        # Just punt and figure Content-Length for all OPTIONS requests.
        if cherrypy.request.method == "OPTIONS":
            stream = False
        
        if stream:
            try:
                del self.headers['Content-Length']
            except KeyError:
                pass
        else:
            # Responses which are not streamed should have a Content-Length,
            # but allow user code to set Content-Length if desired.
            if self.headers.get('Content-Length') is None:
                content = self.collapse_body()
                self.headers['Content-Length'] = len(content)
        
        # Transform our header dict into a sorted list of tuples.
        self.header_list = self.headers.sorted_list()
        
        cookie = self.simple_cookie.output()
        if cookie:
            for line in cookie.split("\n"):
                name, value = line.split(": ", 1)
                self.header_list.append((name, value))
    
    dbltrace = "\n===First Error===\n\n%s\n\n===Second Error===\n\n%s\n\n"
    
    def handleError(self, exc):
        """Set status, headers, and body when an unanticipated error occurs."""
        try:
            cherrypy.request.hooks.run('before_error_response')
            
            _cputil.get_special_attribute('_cp_on_error')()
            self.finalize()
            
            cherrypy.request.hooks.run('after_error_response')
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
        
        # Failure in error hooks or finalize.
        # Bypass them all.
        if cherrypy.config.get('server.show_tracebacks', False):
            body = self.dbltrace % (_cputil.formatExc(exc),
                                    _cputil.formatExc())
        else:
            body = ""
        self.setBareError(body)
    
    def setBareError(self, body=None):
        self.status, self.header_list, self.body = _cputil.bareError(body)

