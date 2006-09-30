"""CherryPy core request/response handling."""

import Cookie
import os
import sys
import time
import types

import cherrypy
from cherrypy import _cpcgifs
from cherrypy._cperror import format_exc, bare_error
from cherrypy.lib import http


class Hook(object):
    """A callback and its metadata: failsafe, priority, and kwargs.
    
    failsafe: If True, the callback is guaranteed to run even if other
        callbacks from the same call point raise exceptions.
    priority: Defines the order of execution for a list of Hooks.
        Defaults to 50. Priority numbers should be limited to the
        closed interval [0, 100], but values outside this range are
        acceptable, as are fractional values.
    """
    
    def __init__(self, callback, failsafe=None, priority=None, **kwargs):
        self.callback = callback
        
        if failsafe is None:
            failsafe = getattr(callback, "failsafe", False)
        self.failsafe = failsafe
        
        if priority is None:
            priority = getattr(callback, "priority", 50)
        self.priority = priority
        
        self.kwargs = kwargs
    
    def __cmp__(self, other):
        return cmp(self.priority, other.priority)
    
    def __call__(self):
        """Run self.callback(**self.kwargs)."""
        return self.callback(**self.kwargs)


class HookMap(dict):
    """A map of call points to lists of callbacks (Hook objects)."""
    
    def __new__(cls, points=None):
        d = dict.__new__(cls)
        for p in points or []:
            d[p] = []
        return d
    
    def __init__(self, *a, **kw):
        pass
    
    def attach(self, point, callback, failsafe=None, priority=None, **kwargs):
        """Append a new Hook made from the supplied arguments."""
        self[point].append(Hook(callback, failsafe, priority, **kwargs))
    
    def run(self, point):
        """Execute all registered Hooks (callbacks) for the given point."""
        if cherrypy.response.timed_out:
            raise cherrypy.TimeoutError()
        
        exc = None
        hooks = self[point]
        hooks.sort()
        for hook in hooks:
            # Some hooks are guaranteed to run even if others at
            # the same hookpoint fail. We will still log the failure,
            # but proceed on to the next hook. The only way
            # to stop all processing from one of these hooks is
            # to raise SystemExit and stop the whole server.
            if exc is None or hook.failsafe:
                try:
                    hook()
                except (KeyboardInterrupt, SystemExit):
                    raise
                except (cherrypy.HTTPError, cherrypy.HTTPRedirect,
                        cherrypy.InternalRedirect):
                    exc = sys.exc_info()[1]
                except:
                    exc = sys.exc_info()[1]
                    cherrypy.log(traceback=True)
        if exc:
            raise
    
    def __copy__(self):
        newmap = self.__class__()
        # We can't just use 'update' because we want copies of the
        # mutable values (each is a list) as well.
        for k, v in self.iteritems():
            newmap[k] = v[:]
        return newmap
    copy = __copy__


class PageHandler(object):
    """Callable which sets response.body."""
    
    def __init__(self, callable, *args, **kwargs):
        self.callable = callable
        self.args = args
        self.kwargs = kwargs
    
    def __call__(self):
        return self.callable(*self.args, **self.kwargs)


class LateParamPageHandler(PageHandler):
    """When passing cherrypy.request.params to the page handler, we do not
    want to capture that dict too early; we want to give tools like the
    decoding tool a chance to modify the params dict in-between the lookup
    of the handler and the actual calling of the handler. This subclass
    takes that into account, and allows request.params to be 'bound late'
    (it's more complicated than that, but that's the effect).
    """
    
    def _get_kwargs(self):
        kwargs = cherrypy.request.params.copy()
        if self._kwargs:
            kwargs.update(self._kwargs)
        return kwargs
    
    def _set_kwargs(self, kwargs):
        self._kwargs = kwargs
    
    kwargs = property(_get_kwargs, _set_kwargs,
                      doc='page handler kwargs (with '
                      'cherrypy.request.params copied in)')


class Dispatcher(object):
    
    def __call__(self, path_info):
        """Set handler and config for the current request."""
        request = cherrypy.request
        func, vpath = self.find_handler(path_info)
        
        if func:
            # Decode any leftover %2F in the virtual_path atoms.
            vpath = [x.replace("%2F", "/") for x in vpath]
            request.handler = LateParamPageHandler(func, *vpath)
        else:
            request.handler = cherrypy.NotFound()
    
    def find_handler(self, path):
        """Find the appropriate page handler for the given path."""
        request = cherrypy.request
        app = request.app
        root = app.root
        
        # Get config for the root object/path.
        curpath = ""
        nodeconf = {}
        if hasattr(root, "_cp_config"):
            nodeconf.update(root._cp_config)
        if "/" in app.config:
            nodeconf.update(app.config["/"])
        object_trail = [('root', root, nodeconf, curpath)]
        
        node = root
        names = [x for x in path.strip('/').split('/') if x] + ['index']
        for name in names:
            # map to legal Python identifiers (replace '.' with '_')
            objname = name.replace('.', '_')
            
            nodeconf = {}
            node = getattr(node, objname, None)
            if node is not None:
                # Get _cp_config attached to this node.
                if hasattr(node, "_cp_config"):
                    nodeconf.update(node._cp_config)
            
            # Mix in values from app.config for this path.
            curpath = "/".join((curpath, name))
            if curpath in app.config:
                nodeconf.update(app.config[curpath])
            
            object_trail.append((objname, node, nodeconf, curpath))
        
        def set_conf():
            """Set cherrypy.request.config."""
            base = cherrypy.config.copy()
            # Note that we merge the config from each node
            # even if that node was None.
            for name, obj, conf, curpath in object_trail:
                base.update(conf)
                if 'tools.staticdir.dir' in conf:
                    base['tools.staticdir.section'] = curpath
            return base
        
        # Try successive objects (reverse order)
        num_candidates = len(object_trail) - 1
        for i in xrange(num_candidates, -1, -1):
            
            name, candidate, nodeconf, curpath = object_trail[i]
            if candidate is None:
                continue
            
            # Try a "default" method on the current leaf.
            if hasattr(candidate, "default"):
                defhandler = candidate.default
                if getattr(defhandler, 'exposed', False):
                    # Insert any extra _cp_config from the default handler.
                    conf = getattr(defhandler, "_cp_config", {})
                    object_trail.insert(i+1, ("default", defhandler, conf, curpath))
                    request.config = set_conf()
                    request.is_index = False
                    return defhandler, names[i:-1]
            
            # Uncomment the next line to restrict positional params to "default".
            # if i < num_candidates - 2: continue
            
            # Try the current leaf.
            if getattr(candidate, 'exposed', False):
                request.config = set_conf()
                if i == num_candidates:
                    # We found the extra ".index". Mark request so tools
                    # can redirect if path_info has no trailing slash.
                    request.is_index = True
                else:
                    # We're not at an 'index' handler. Mark request so tools
                    # can redirect if path_info has NO trailing slash.
                    # Note that this also includes handlers which take
                    # positional parameters (virtual paths).
                    request.is_index = False
                return candidate, names[i:-1]
        
        # We didn't find anything
        request.config = set_conf()
        return None, []


class MethodDispatcher(Dispatcher):
    """Additional dispatch based on cherrypy.request.method.upper().
    
    Methods named GET, POST, etc will be called on an exposed class.
    The method names must be all caps; the appropriate Allow header
    will be output showing all capitalized method names as allowable
    HTTP verbs.
    
    Note that the containing class must be exposed, not the methods.
    """
    
    def __call__(self, path_info):
        """Set handler and config for the current request."""
        request = cherrypy.request
        resource, vpath = self.find_handler(path_info)
        
        if resource:
            # Set Allow header
            avail = [m for m in dir(resource) if m.isupper()]
            if "GET" in avail and "HEAD" not in avail:
                avail.append("HEAD")
            avail.sort()
            cherrypy.response.headers['Allow'] = ", ".join(avail)
            
            # Find the subhandler
            meth = request.method.upper()
            func = getattr(resource, meth, None)
            if func is None and meth == "HEAD":
                func = getattr(resource, "GET", None)
            if func:
                # Decode any leftover %2F in the virtual_path atoms.
                vpath = [x.replace("%2F", "/") for x in vpath]
                request.handler = LateParamPageHandler(func, *vpath)
            else:
                request.handler = cherrypy.HTTPError(405)
        else:
            request.handler = cherrypy.NotFound()


# Config namespace handlers
def tools_namespace(k, v):
    """Attach tools specified in config."""
    toolname, arg = k.split(".", 1)
    bucket = cherrypy.request.toolmap.setdefault(toolname, {})
    bucket[arg] = v

def hooks_namespace(k, v):
    """Attach bare hooks declared in config."""
    # Use split again to allow multiple hooks for a single
    # hookpoint per path (e.g. "hooks.before_handler.1").
    # Little-known fact you only get from reading source ;)
    hookpoint = k.split(".", 1)[0]
    if isinstance(v, basestring):
        v = cherrypy.lib.attributes(v)
    if not isinstance(v, Hook):
        v = Hook(v)
    cherrypy.request.hooks[hookpoint].append(v)

def request_namespace(k, v):
    """Attach request attributes declared in config."""
    setattr(cherrypy.request, k, v)

def response_namespace(k, v):
    """Attach response attributes declared in config."""
    setattr(cherrypy.response, k, v)

def error_page_namespace(k, v):
    """Attach error pages declared in config."""
    cherrypy.request.error_page[int(k)] = v


hookpoints = ['on_start_resource', 'before_request_body',
              'before_handler', 'before_finalize',
              'on_end_resource', 'on_end_request',
              'before_error_response', 'after_error_response']


class Request(object):
    """An HTTP request."""
    
    # Conversation/connection attributes
    local = http.Host("localhost", 80)
    remote = http.Host("localhost", 1111)
    scheme = "http"
    server_protocol = "HTTP/1.1"
    base = ""
    
    # Request-Line attributes
    request_line = ""
    method = "GET"
    query_string = ""
    protocol = (1, 1)
    params = {}
    
    # Message attributes
    header_list = []
    headers = http.HeaderMap()
    cookie = Cookie.SimpleCookie()
    rfile = None
    process_request_body = True
    methods_with_bodies = ("POST", "PUT")
    body = None
    body_read = False
    headers_read = False
    
    # Dispatch attributes
    dispatch = Dispatcher()
    script_name = ""
    path_info = "/"
    app = None
    handler = None
    toolmap = {}
    config = None
    recursive_redirect = False
    is_index = None
    
    hooks = HookMap(hookpoints)
    
    error_response = cherrypy.HTTPError(500).set_response
    error_page = {}
    show_tracebacks = True
    throw_errors = False
    
    namespaces = {"tools": tools_namespace,
                  "hooks": hooks_namespace,
                  "request": request_namespace,
                  "response": response_namespace,
                  "error_page": error_page_namespace,
                  }
    
    def __init__(self, local_host, remote_host, scheme="http",
                 server_protocol="HTTP/1.1"):
        """Populate a new Request object.
        
        local_host should be an http.Host object with the server info.
        remote_host should be an http.Host object with the client info.
        scheme should be a string, either "http" or "https".
        """
        self.local = local_host
        self.remote = remote_host
        self.scheme = scheme
        self.server_protocol = server_protocol
        
        self.closed = False
        self.redirections = []
        
        # Put a *copy* of the class error_page into self.
        self.error_page = self.error_page.copy()
        
        # Put a *copy* of the class namespaces into self.
        self.namespaces = self.namespaces.copy()
    
    def close(self):
        if not self.closed:
            self.closed = True
            self.hooks.run('on_end_request')
            
            s = (self, cherrypy._serving.response)
            try:
                cherrypy.engine.servings.remove(s)
            except ValueError:
                pass
            
            cherrypy._serving.__dict__.clear()
    
    def run(self, method, path, query_string, req_protocol, headers, rfile):
        """Process the Request.
        
        method, path, query_string, and req_protocol should be pulled directly
            from the Request-Line (e.g. "GET /path?key=val HTTP/1.0").
        path should be %XX-unquoted, but query_string should not be.
        headers should be a list of (name, value) tuples.
        rfile should be a file-like object containing the HTTP request entity.
        
        When run() is done, the returned object should have 3 attributes:
          status, e.g. "200 OK"
          header_list, a list of (name, value) tuples
          body, an iterable yielding strings
        
        Consumer code (HTTP servers) should then access these response
        attributes to build the outbound stream.
        
        """
        
        try:
            self.error_response = cherrypy.HTTPError(500).set_response
            
            self.method = method
            path = path or "/"
            self.query_string = query_string or ''
            
            # Compare request and server HTTP protocol versions, in case our
            # server does not support the requested protocol. Limit our output
            # to min(req, server). We want the following output:
            #     request    server     actual written   supported response
            #     protocol   protocol  response protocol    feature set
            # a     1.0        1.0           1.0                1.0
            # b     1.0        1.1           1.1                1.0
            # c     1.1        1.0           1.0                1.0
            # d     1.1        1.1           1.1                1.1
            # Notice that, in (b), the response will be "HTTP/1.1" even though
            # the client only understands 1.0. RFC 2616 10.5.6 says we should
            # only return 505 if the _major_ version is different.
            rp = int(req_protocol[5]), int(req_protocol[7])
            sp = int(self.server_protocol[5]), int(self.server_protocol[7])
            self.protocol = min(rp, sp)
            
            # Rebuild first line of the request (e.g. "GET /path HTTP/1.0").
            url = path
            if query_string:
                url += '?' + query_string
            self.request_line = '%s %s %s' % (method, url, req_protocol)
            
            self.header_list = list(headers)
            self.rfile = rfile
            self.headers = http.HeaderMap()
            self.cookie = Cookie.SimpleCookie()
            self.handler = None
            
            # path_info should be the path from the
            # app root (script_name) to the handler.
            self.script_name = self.app.script_name
            self.path_info = path[len(self.script_name.rstrip("/")):]
            
            # Loop to allow for InternalRedirect.
            pi = self.path_info
            while True:
                try:
                    self.respond(pi)
                    break
                except cherrypy.InternalRedirect, ir:
                    pi = ir.path
                    if pi in self.redirections and not self.recursive_redirect:
                        raise RuntimeError("InternalRedirect visited the "
                                           "same URL twice: %s" % repr(pi))
                    self.redirections.append(pi)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            if self.throw_errors:
                raise
            else:
                # Can't use handle_error because we may not have hooks yet.
                cherrypy.log(traceback=True)
                
                # Failure in setup, error handler or finalize. Bypass them.
                if self.show_tracebacks:
                    body = format_exc()
                else:
                    body = ""
                r = bare_error(body)
                response = cherrypy.response
                response.status, response.header_list, response.body = r
        
        if self.method == "HEAD":
            # HEAD requests MUST NOT return a message-body in the response.
            cherrypy.response.body = []
        
        cherrypy.log.access()
        
        return cherrypy.response
    
    def respond(self, path_info):
        """Generate a response for the resource at self.path_info."""
        try:
            try:
                try:
                    if cherrypy.response.timed_out:
                        raise cherrypy.TimeoutError()
                    
                    if self.app is None:
                        raise cherrypy.NotFound()
                    
                    if not self.headers_read:
                        # Get the 'Host' header, so we can do HTTPRedirects properly.
                        self.process_headers()
                    
                    # Make a copy of the class hooks
                    self.hooks = self.__class__.hooks.copy()
                    self.get_resource(path_info)
                    self.configure()
                    
                    self.hooks.run('on_start_resource')
                    
                    if not self.body_read:
                        if self.process_request_body:
                            if self.method not in self.methods_with_bodies:
                                self.process_request_body = False
                        
                        if self.process_request_body:
                            # Prepare the SizeCheckWrapper for the request body
                            mbs = cherrypy.server.max_request_body_size
                            if mbs > 0:
                                self.rfile = http.SizeCheckWrapper(self.rfile, mbs)
                    
                    self.hooks.run('before_request_body')
                    if self.process_request_body:
                        self.process_body()
                    
                    self.hooks.run('before_handler')
                    if self.handler:
                        cherrypy.response.body = self.handler()
                    self.hooks.run('before_finalize')
                    cherrypy.response.finalize()
                except (cherrypy.HTTPRedirect, cherrypy.HTTPError), inst:
                    inst.set_response()
                    self.hooks.run('before_finalize')
                    cherrypy.response.finalize()
            finally:
                self.hooks.run('on_end_resource')
        except (KeyboardInterrupt, SystemExit, cherrypy.InternalRedirect):
            raise
        except:
            if self.throw_errors:
                raise
            self.handle_error(sys.exc_info())
    
    def process_headers(self):
        # Guard against re-reading body (e.g. on InternalRedirect)
        if self.headers_read:
            return
        self.headers_read = True
        
        self.params = http.parse_query_string(self.query_string)
        
        # Process the headers into self.headers
        headers = self.headers
        for name, value in self.header_list:
            # Call title() now (and use dict.__method__(headers))
            # so title doesn't have to be called twice.
            name = name.title()
            value = value.strip()
            
            # Warning: if there is more than one header entry for cookies (AFAIK,
            # only Konqueror does that), only the last one will remain in headers
            # (but they will be correctly stored in request.cookie).
            if "=?" in value:
                dict.__setitem__(headers, name, http.decode_TEXT(value))
            else:
                dict.__setitem__(headers, name, value)
            
            # Handle cookies differently because on Konqueror, multiple
            # cookies come on different lines with the same key
            if name == 'Cookie':
                self.cookie.load(value)
        
        if not dict.__contains__(headers, 'Host'):
            # All Internet-based HTTP/1.1 servers MUST respond with a 400
            # (Bad Request) status code to any HTTP/1.1 request message
            # which lacks a Host header field.
            if self.protocol >= (1, 1):
                msg = "HTTP/1.1 requires a 'Host' request header."
                raise cherrypy.HTTPError(400, msg)
        host = dict.__getitem__(headers, 'Host')
        if not host:
            host = self.local.name or self.local.ip
        self.base = "%s://%s" % (self.scheme, host)
    
    def get_resource(self, path):
        """Find and call a dispatcher (which sets self.handler and .config)."""
        dispatch = self.dispatch
        # First, see if there is a custom dispatch at this URI. Custom
        # dispatchers can only be specified in app.config, not in _cp_config
        # (since custom dispatchers may not even have an app.root).
        trail = path
        while trail:
            nodeconf = self.app.config.get(trail, {})
            
            d = nodeconf.get("request.dispatch")
            if d:
                dispatch = d
                break
            
            lastslash = trail.rfind("/")
            if lastslash == -1:
                break
            elif lastslash == 0 and trail != "/":
                trail = "/"
            else:
                trail = trail[:lastslash]
        
        # dispatch() should set self.handler and self.config
        dispatch(path)
    
    def configure(self):
        """Process self.config, populate self.toolmap and set up each tool."""
        self.toolmap = tm = {}
        
        # Process config namespaces (including tools.*)
        reqconf = self.config
        for k in reqconf:
            atoms = k.split(".", 1)
            namespace = atoms[0]
            if namespace in self.namespaces:
                self.namespaces[namespace](atoms[1], reqconf[k])
        
        # Run tool._setup(conf) for each tool in the new toolmap.
        tools = cherrypy.tools
        for toolname in tm:
            if tm[toolname].get("on", False):
                tool = getattr(tools, toolname)
                tool._setup()
    
    def process_body(self):
        """Convert request.rfile into request.params (or request.body)."""
        # Guard against re-reading body (e.g. on InternalRedirect)
        if self.body_read:
            return
        self.body_read = True
        
        # FieldStorage only recognizes POST, so fake it.
        methenv = {'REQUEST_METHOD': "POST"}
        try:
            forms = _cpcgifs.FieldStorage(fp=self.rfile,
                                          headers=self.headers,
                                          environ=methenv,
                                          keep_blank_values=1)
        except http.MaxSizeExceeded:
            # Post data is too big
            raise cherrypy.HTTPError(413)
        
        if forms.file:
            # request body was a content-type other than form params.
            self.body = forms.file
        else:
            self.params.update(http.params_from_CGI_form(forms))
    
    def handle_error(self, exc):
        try:
            self.hooks.run("before_error_response")
            if self.error_response:
                self.error_response()
            self.hooks.run("after_error_response")
            cherrypy.response.finalize()
        except cherrypy.HTTPRedirect, inst:
            inst.set_response()
            cherrypy.response.finalize()


def file_generator(input, chunkSize=65536):
    """Yield the given input (a file object) in chunks (default 64k)."""
    chunk = input.read(chunkSize)
    while chunk:
        yield chunk
        chunk = input.read(chunkSize)
    input.close()


class Body(object):
    """The body of the HTTP response (the response entity)."""
    
    def __get__(self, obj, objclass=None):
        if obj is None:
            # When calling on the class instead of an instance...
            return self
        else:
            return obj._body
    
    def __set__(self, obj, value):
        if cherrypy.response.timed_out:
            raise cherrypy.TimeoutError()
        # Convert the given value to an iterable object.
        if isinstance(value, basestring):
            # strings get wrapped in a list because iterating over a single
            # item list is much faster than iterating over every character
            # in a long string.
            value = [value]
        elif isinstance(value, types.FileType):
            value = file_generator(value)
        elif isinstance(value, types.GeneratorType):
            value = flattener(value)
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
    
    # Class attributes for dev-time introspection.
    status = ""
    header_list = []
    headers = http.HeaderMap()
    cookie = Cookie.SimpleCookie()
    body = Body()
    time = None
    timeout = 300
    timed_out = False
    stream = False
    
    def __init__(self):
        self.status = None
        self.header_list = None
        self._body = []
        self.time = time.time()
        
        self.headers = http.HeaderMap()
        # Since we know all our keys are titled strings, we can
        # bypass HeaderMap.update and get a big speed boost.
        dict.update(self.headers, {
            "Content-Type": 'text/html',
            "Server": "CherryPy/" + cherrypy.__version__,
            "Date": http.HTTPDate(self.time),
        })
        self.cookie = Cookie.SimpleCookie()
    
    def collapse_body(self):
        newbody = ''.join([chunk for chunk in self.body])
        self.body = newbody
        return newbody
    
    def finalize(self):
        """Transform headers (and cookies) into cherrypy.response.header_list."""
        if self.timed_out:
            raise cherrypy.TimeoutError()
        
        try:
            code, reason, _ = http.valid_status(self.status)
        except ValueError, x:
            raise cherrypy.HTTPError(500, x.args[0])
        
        self.status = "%s %s" % (code, reason)
        
        headers = self.headers
        if self.stream:
            headers.pop('Content-Length', None)
        else:
            # Responses which are not streamed should have a Content-Length,
            # but allow user code to set Content-Length if desired.
            if (dict.get(headers, 'Content-Length') is None
                    and code not in (304,)):
                content = self.collapse_body()
                dict.__setitem__(headers, 'Content-Length', len(content))
        
        # Transform our header dict into a list of tuples.
        self.header_list = h = headers.output(cherrypy.request.protocol)
        
        cookie = self.cookie.output()
        if cookie:
            for line in cookie.split("\n"):
                name, value = line.split(": ", 1)
                h.append((name, value))
    
    def check_timeout(self):
        """If now > self.time + self.timeout, set self.timed_out.
        
        This purposefully sets a flag, rather than raising an error,
        so that a monitor thread can interrupt the Response thread.
        """
        if time.time() > self.time + self.timeout:
            self.timed_out = True

