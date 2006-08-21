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


class HookMap(object):
    
    def __init__(self, points=None, failsafe=None):
        points = points or []
        self.callbacks = dict([(point, []) for point in points])
        self.failsafe = failsafe or []
    
    def attach(self, point, callback, conf=None):
        if not conf:
            # No point adding a wrapper if there's no conf
            self.callbacks[point].append(callback)
        else:
            def wrapper():
                callback(**conf)
            self.callbacks[point].append(wrapper)
    
    def run(self, point):
        """Execute all registered callbacks for the given point."""
        if cherrypy.response.timed_out:
            raise cherrypy.TimeoutError()
        
        failsafe = point in self.failsafe
        for callback in self.callbacks[point]:
            # Some hookpoints guarantee all callbacks are run even if
            # others at the same hookpoint fail. We will still log the
            # failure, but proceed on to the next callback. The only way
            # to stop all processing from one of these callbacks is
            # to raise SystemExit and stop the whole server. So, trap
            # your own errors in these callbacks!
            if failsafe:
                try:
                    callback()
                except (KeyboardInterrupt, SystemExit):
                    raise
                except:
                    cherrypy.log(traceback=True)
            else:
                callback()


class Request(object):
    """An HTTP request."""
    
    # Conversation/connection attributes
    local = http.Host("localhost", 80)
    remote = http.Host("localhost", 1111)
    scheme = "http"
    base = ""
    
    # Request-Line attributes
    request_line = ""
    method = "GET"
    path = ""
    query_string = ""
    protocol = (1, 1)
    params = {}
    
    # Message attributes
    header_list = []
    headers = http.HeaderMap()
    simple_cookie = Cookie.SimpleCookie()
    rfile = None
    process_request_body = True
    body = None
    body_read = False
    
    # Dispatch attributes
    script_name = ""
    path_info = "/"
    app = None
    handler = None
    toolmap = {}
    config = None
    error_response = cherrypy.HTTPError(500).set_response
    hookpoints = ['on_start_resource', 'before_request_body',
                  'before_main', 'before_finalize',
                  'on_end_resource', 'on_end_request',
                  'before_error_response', 'after_error_response']
    hooks = HookMap(hookpoints)
    
    def __init__(self, local_host, remote_host, scheme="http"):
        """Populate a new Request object.
        
        local_host should be an http.Host object with the server info.
        remote_host should be an http.Host object with the client info.
        scheme should be a string, either "http" or "https".
        """
        self.local = local_host
        self.remote = remote_host
        self.scheme = scheme
        
        self.closed = False
        self.redirections = []
    
    def close(self):
        if not self.closed:
            self.closed = True
            self.hooks.run('on_end_request')
            
            s = (self, cherrypy.serving.response)
            try:
                cherrypy.engine.servings.remove(s)
            except ValueError:
                pass
            
            cherrypy.serving.__dict__.clear()
    
    def run(self, method, path, query_string, protocol, headers, rfile):
        """Process the Request.
        
        method, path, query_string, and protocol should be pulled directly
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
            self.path = path or "/"
            self.query_string = query_string
            self.protocol = int(protocol[5]), int(protocol[7])
            
            # Rebuild first line of the request (e.g. "GET /path HTTP/1.0").
            url = path
            if query_string:
                url += '?' + query_string
            self.request_line = '%s %s %s' % (method, url, protocol)
            
            self.header_list = list(headers)
            self.rfile = rfile
            self.headers = http.HeaderMap()
            self.simple_cookie = Cookie.SimpleCookie()
            self.handler = None
            
            # Get the 'Host' header, so we can do HTTPRedirects properly.
            self.process_headers()
            
            # path_info should be the path from the
            # app root (script_name) to the handler.
            self.script_name = self.app.script_name
            self.path_info = self.path[len(self.script_name.rstrip("/")):]
            
            # Loop to allow for InternalRedirect.
            pi = self.path_info
            while True:
                try:
                    self.respond(pi)
                    break
                except cherrypy.InternalRedirect, ir:
                    pi = ir.path
                    if (pi in self.redirections and
                        not cherrypy.config.get("recursive_redirect")):
                        raise RuntimeError("InternalRedirect visited the "
                                           "same URL twice: %s" % repr(pi))
                    self.redirections.append(pi)
        except (KeyboardInterrupt, SystemExit):
            raise
        except cherrypy.TimeoutError:
            raise
        except:
            if cherrypy.config.get("throw_errors", False):
                raise
            self.handle_error(sys.exc_info())
        
        if self.method == "HEAD":
            # HEAD requests MUST NOT return a message-body in the response.
            cherrypy.response.body = []
        
        log_access = cherrypy.config.get("log_access", cherrypy.log_access)
        if log_access:
            log_access()
        
        return cherrypy.response
    
    def respond(self, path_info):
        """Generate a response for the resource at self.path_info."""
        try:
            try:
                if cherrypy.response.timed_out:
                    raise cherrypy.TimeoutError()
                
                if self.app is None:
                    raise cherrypy.NotFound()
                
                self.hooks = HookMap(self.hookpoints)
                self.hooks.failsafe = ['on_start_resource', 'on_end_resource',
                                       'on_end_request']
                
                self.get_resource(path_info)
                self.tool_up()
                self.hooks.run('on_start_resource')
                
                if self.process_request_body and not self.body_read:
                    # Check path-specific methods_with_bodies.
                    meths = self.config.get("methods_with_bodies", ("POST", "PUT"))
                    self.process_request_body = self.method in meths
                    
                    # Prepare the SizeCheckWrapper for the request body
                    mbs = int(self.config.get('server.max_request_body_size',
                                              100 * 1024 * 1024))
                    if mbs > 0:
                        self.rfile = http.SizeCheckWrapper(self.rfile, mbs)
                
                self.hooks.run('before_request_body')
                if self.process_request_body:
                    self.process_body()
                
                self.hooks.run('before_main')
                if self.handler:
                    self.handler()
                self.hooks.run('before_finalize')
                cherrypy.response.finalize()
            except (cherrypy.HTTPRedirect, cherrypy.HTTPError), inst:
                inst.set_response()
                self.hooks.run('before_finalize')
                cherrypy.response.finalize()
        finally:
            self.hooks.run('on_end_resource')
    
    def process_headers(self):
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
            # (but they will be correctly stored in request.simple_cookie).
            if "=?" in value:
                dict.__setitem__(headers, name, http.decode_TEXT(value))
            else:
                dict.__setitem__(headers, name, value)
            
            # Handle cookies differently because on Konqueror, multiple
            # cookies come on different lines with the same key
            if name == 'Cookie':
                self.simple_cookie.load(value)
        
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
        dispatch = default_dispatch
        # First, see if there is a custom dispatch at this URI. Custom
        # dispatchers can only be specified in app.conf, not in _cp_config
        # (since custom dispatchers may not even have an app.root).
        trail = path
        while trail:
            nodeconf = self.app.conf.get(trail, {})
            d = nodeconf.get("dispatch")
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
    
    def tool_up(self):
        """Populate self.toolmap and set up each tool."""
        # Get all 'tools.*' config entries as a {toolname: {k: v}} dict.
        self.toolmap = tm = {}
        reqconf = self.config
        for k in reqconf:
            atoms = k.split(".", 2)
            namespace = atoms[0]
            if namespace == "tools":
                toolname = atoms[1]
                bucket = tm.setdefault(toolname, {})
                bucket[atoms[2]] = reqconf[k]
            elif namespace == "hooks":
                # Attach bare hooks declared in config.
                hookpoint = atoms[1]
                v = reqconf[k]
                if isinstance(v, basestring):
                    v = cherrypy.lib.attributes(v)
                self.hooks.attach(hookpoint, v)
        
        # Run tool._setup(conf) for each tool in the new toolmap.
        tools = cherrypy.tools
        for toolname in tm:
            if tm[toolname].get("on", False):
                tool = getattr(tools, toolname)
                tool._setup()
    
    def _get_browser_url(self):
        url = self.base + self.path
        if self.query_string:
            url += '?' + self.query_string
        return url
    browser_url = property(_get_browser_url,
                          doc="The URL as entered in a browser (read-only).")
    
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
        response = cherrypy.response
        try:
            self.hooks.run("before_error_response")
            if self.error_response:
                self.error_response()
            self.hooks.run("after_error_response")
            response.finalize()
            return
        except cherrypy.HTTPRedirect, inst:
            try:
                inst.set_response()
                response.finalize()
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
        
        # Failure in error handler or finalize. Bypass them.
        if cherrypy.config.get('show_tracebacks', False):
            dbltrace = ("\n===First Error===\n\n%s"
                        "\n\n===Second Error===\n\n%s\n\n")
            body = dbltrace % (format_exc(exc), format_exc())
        else:
            body = ""
        r = bare_error(body)
        response.status, response.header_list, response.body = r


class PageHandler(object):
    """Callable which sets response.body."""
    
    def __init__(self, callable, *args, **kwargs):
        self.callable = callable
        self.args = args
        self.kwargs = kwargs
    
    def __call__(self):
        cherrypy.response.body = self.callable(*self.args, **self.kwargs)


class LateParamPageHandler(PageHandler):
    """When passing cherrypy.request.params to the page handler, we don't
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
        environments = cherrypy.config.environments
        curpath = ""
        nodeconf = {}
        if hasattr(root, "_cp_config"):
            nodeconf.update(root._cp_config)
        if 'environment' in nodeconf:
            env = environments[nodeconf['environment']]
            for k in env:
                if k not in nodeconf:
                    nodeconf[k] = env[k]
        if "/" in app.conf:
            nodeconf.update(app.conf["/"])
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
                    
                    # Resolve "environment" entries. This must be done node-by-node
                    # so that a child's "environment" can override concrete settings
                    # of a parent. However, concrete settings in this node will
                    # override "environment" settings in the same node.
                    if 'environment' in nodeconf:
                        env = environments[nodeconf['environment']]
                        for k in env:
                            if k not in nodeconf:
                                nodeconf[k] = env[k]
            
            # Mix in values from app.conf for this path.
            curpath = "/".join((curpath, name))
            if curpath in app.conf:
                nodeconf.update(app.conf[curpath])
            
            object_trail.append((objname, node, nodeconf, curpath))
        
        def set_conf():
            """Set cherrypy.request.config."""
            base = cherrypy.config.globalconf.copy()
            # Note that we merge the config from each node
            # even if that node was None.
            for name, obj, conf, curpath in object_trail:
                base.update(conf)
                if 'tools.staticdir.dir' in conf:
                    base['tools.staticdir.section'] = curpath
            return base
        
        # Try successive objects (reverse order)
        for i in xrange(len(object_trail) - 1, -1, -1):
            
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
                    return defhandler, names[i:-1]
            
            # Uncomment the next line to restrict positional params to "default".
            # if i < len(object_trail) - 2: continue
            
            # Try the current leaf.
            if getattr(candidate, 'exposed', False):
                request.config = set_conf()
                if i == len(object_trail) - 1:
                    # We found the extra ".index". Check if the original path
                    # had a trailing slash (otherwise, do a redirect).
                    if path[-1:] != '/':
                        atoms = request.browser_url.split("?", 1)
                        new_url = atoms.pop(0) + '/'
                        if atoms:
                            new_url += "?" + atoms[0]
                        raise cherrypy.HTTPRedirect(new_url)
                return candidate, names[i:-1]
        
        # We didn't find anything
        request.config = set_conf()
        return None, []

default_dispatch = Dispatcher()


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
        
        # Decode any leftover %2F in the virtual_path atoms.
        vpath = [x.replace("%2F", "/") for x in vpath]
        
        if resource:
            # Set Allow header
            avail = [m for m in dir(resource) if m.isupper()]
            if "GET" in avail and "HEAD" not in avail:
                avail.append("HEAD")
            avail.sort()
            cherrypy.response.headers['Allow'] = ", ".join(avail)
            
            # Find the subhandler
            meth = cherrypy.request.method.upper()
            func = getattr(resource, meth, None)
            if func is None and meth == "HEAD":
                func = getattr(resource, "GET", None)
            if func:
                request.handler = LateParamPageHandler(func, *vpath)
            else:
                request.handler = cherrypy.HTTPError(405)
        else:
            request.handler = cherrypy.NotFound()


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
        if isinstance(value, types.FileType):
            value = file_generator(value)
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
    
    # Class attributes for dev-time introspection.
    status = ""
    header_list = []
    headers = http.HeaderMap()
    simple_cookie = Cookie.SimpleCookie()
    body = Body()
    time = None
    timed_out = False
    
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
        self.simple_cookie = Cookie.SimpleCookie()
    
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
        
        stream = cherrypy.config.get("stream_response", False)
        # OPTIONS requests MUST include a Content-Length of 0 if no body.
        # Just punt and figure Content-Length for all OPTIONS requests.
        if cherrypy.request.method == "OPTIONS":
            stream = False
        
        headers = self.headers
        if stream:
            headers.pop('Content-Length', None)
        else:
            # Responses which are not streamed should have a Content-Length,
            # but allow user code to set Content-Length if desired.
            if (dict.get(headers, 'Content-Length') is None
                    and code not in (304,)):
                content = self.collapse_body()
                dict.__setitem__(headers, 'Content-Length', len(content))
        
        # Transform our header dict into a sorted list of tuples.
        self.header_list = h = headers.output(cherrypy.request.protocol)
        
        cookie = self.simple_cookie.output()
        if cookie:
            for line in cookie.split("\n"):
                name, value = line.split(": ", 1)
                h.append((name, value))
    
    def check_timeout(self):
        """If now > self.time + deadlock_timeout, set self.timed_out.
        
        This purposefully sets a flag, rather than raising an error,
        so that a monitor thread can interrupt the Response thread.
        """
        timeout = float(cherrypy.config.get('deadlock_timeout', 300))
        if time.time() > self.time + timeout:
            self.timed_out = True

