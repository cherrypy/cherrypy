"""WSGI interface (see PEP 333)."""

import StringIO as _StringIO
import sys as _sys

import cherrypy as _cherrypy
from cherrypy import _cperror, wsgiserver
from cherrypy.lib import http as _http


class VirtualHost(object):
    """Select a different WSGI application based on the Host header.
    
    This can be useful when running multiple sites within one CP server.
    It allows several domains to point to different applications. For example:
    
        root = Root()
        RootApp = cherrypy.Application(root)
        Domain2App = cherrypy.Application(root)
        SecureApp = cherrypy.Application(Secure())
        
        vhost = cherrypy._cpwsgi.VirtualHost(RootApp,
            domains={'www.domain2.example': Domain2App,
                     'www.domain2.example:443': SecureApp,
                     })
        
        cherrypy.tree.graft(vhost)
    
    default: required. The default WSGI application.
    
    use_x_forwarded_host: if True (the default), any "X-Forwarded-Host"
        request header will be used instead of the "Host" header. This
        is commonly added by HTTP servers (such as Apache) when proxying.
    
    domains: a dict of {host header value: application} pairs.
        The incoming "Host" request header is looked up in this dict,
        and, if a match is found, the corresponding WSGI application
        will be called instead of the default. Note that you often need
        separate entries for "example.com" and "www.example.com".
        In addition, "Host" headers may contain the port number.
    """
    
    def __init__(self, default, domains=None, use_x_forwarded_host=True):
        self.default = default
        self.domains = domains or {}
        self.use_x_forwarded_host = use_x_forwarded_host
    
    def __call__(self, environ, start_response):
        domain = environ.get('HTTP_HOST', '')
        if self.use_x_forwarded_host:
            domain = environ.get("HTTP_X_FORWARDED_HOST", domain)
        
        nextapp = self.domains.get(domain)
        if nextapp is None:
            nextapp = self.default
        return nextapp(environ, start_response)



#                           WSGI-to-CP Adapter                           #


class AppResponse(object):
    
    throws = (KeyboardInterrupt, SystemExit, _cherrypy.InternalRedirect)
    request = None
    
    def __init__(self, environ, start_response, cpapp):
        self.cpapp = cpapp
        
        try:
            self.request = self.get_request(environ)
            
            meth = environ['REQUEST_METHOD']
            path = _http.urljoin(environ.get('SCRIPT_NAME', ''),
                                 environ.get('PATH_INFO', ''))
            qs = environ.get('QUERY_STRING', '')
            rproto = environ.get('SERVER_PROTOCOL')
            headers = self.translate_headers(environ)
            rfile = environ['wsgi.input']
            
            response = self.request.run(meth, path, qs, rproto, headers, rfile)
            s, h, b = response.status, response.header_list, response.body
            exc = None
        except self.throws:
            self.close()
            raise
        except:
            if getattr(self.request, "throw_errors", False):
                self.close()
                raise
            
            tb = _cperror.format_exc()
            _cherrypy.log(tb)
            if not getattr(self.request, "show_tracebacks", True):
                tb = ""
            s, h, b = _cperror.bare_error(tb)
            exc = _sys.exc_info()
        
        self.iter_response = iter(b)
        
        try:
            start_response(s, h, exc)
        except self.throws:
            self.close()
            raise
        except:
            if getattr(self.request, "throw_errors", False):
                self.close()
                raise
            
            _cherrypy.log(traceback=True)
            self.close()
            
            # CherryPy test suite expects bare_error body to be output,
            # so don't call start_response (which, according to PEP 333,
            # may raise its own error at that point).
            s, h, b = _cperror.bare_error()
            self.iter_response = iter(b)
    
    def __iter__(self):
        return self
    
    def next(self):
        try:
            chunk = self.iter_response.next()
            # WSGI requires all data to be of type "str". This coercion should
            # not take any time at all if chunk is already of type "str".
            # If it's unicode, it could be a big performance hit (x ~500).
            if not isinstance(chunk, str):
                chunk = chunk.encode("ISO-8859-1")
            return chunk
        except self.throws:
            raise
        except StopIteration:
            raise
        except:
            if getattr(self.request, "throw_errors", False):
                raise
            
            _cherrypy.log(traceback=True)
            
            # CherryPy test suite expects bare_error body to be output,
            # so don't call start_response (which, according to PEP 333,
            # may raise its own error at that point).
            s, h, b = _cperror.bare_error()
            self.iter_response = iter([])
            return "".join(b)
    
    def close(self):
        """Close and de-reference the current request and response. (Core)"""
        self.cpapp.release_serving()
    
    def get_request(self, environ):
        """Create a Request object using environ."""
        env = environ.get
        
        local = _http.Host('', int(env('SERVER_PORT', 80)),
                           env('SERVER_NAME', ''))
        remote = _http.Host(env('REMOTE_ADDR', ''),
                            int(env('REMOTE_PORT', -1)),
                            env('REMOTE_HOST', ''))
        scheme = env('wsgi.url_scheme')
        sproto = env('ACTUAL_SERVER_PROTOCOL', "HTTP/1.1")
        request, resp = self.cpapp.get_serving(local, remote, scheme, sproto)
        
        # LOGON_USER is served by IIS, and is the name of the
        # user after having been mapped to a local account.
        # Both IIS and Apache set REMOTE_USER, when possible.
        request.login = env('LOGON_USER') or env('REMOTE_USER') or None
        request.multithread = environ['wsgi.multithread']
        request.multiprocess = environ['wsgi.multiprocess']
        request.wsgi_environ = environ
        request.prev = env('cherrypy.request')
        environ['cherrypy.request'] = request
        return request
    
    headerNames = {'HTTP_CGI_AUTHORIZATION': 'Authorization',
                   'CONTENT_LENGTH': 'Content-Length',
                   'CONTENT_TYPE': 'Content-Type',
                   'REMOTE_HOST': 'Remote-Host',
                   'REMOTE_ADDR': 'Remote-Addr',
                   }
    
    def translate_headers(self, environ):
        """Translate CGI-environ header names to HTTP header names."""
        for cgiName in environ:
            # We assume all incoming header keys are uppercase already.
            if cgiName in self.headerNames:
                yield self.headerNames[cgiName], environ[cgiName]
            elif cgiName[:5] == "HTTP_":
                # Hackish attempt at recovering original header names.
                translatedHeader = cgiName[5:].replace("_", "-")
                yield translatedHeader, environ[cgiName]


class CPWSGIApp(object):
    """A WSGI application object for a CherryPy Application.
    
    pipeline: a list of (name, wsgiapp) pairs. Each 'wsgiapp' MUST be a
        constructor that takes an initial, positional 'nextapp' argument,
        plus optional keyword arguments, and returns a WSGI application
        (that takes environ and start_response arguments). The 'name' can
        be any you choose, and will correspond to keys in self.config.
    
    head: rather than nest all apps in the pipeline on each call, it's only
        done the first time, and the result is memoized into self.head. Set
        this to None again if you change self.pipeline after calling self.
    
    config: a dict whose keys match names listed in the pipeline. Each
        value is a further dict which will be passed to the corresponding
        named WSGI callable (from the pipeline) as keyword arguments.
    """
    
    pipeline = [('iredir', InternalRedirector)]
    head = None
    config = {}
    
    response_class = AppResponse
    
    def __init__(self, cpapp, pipeline=None):
        self.cpapp = cpapp
        self.pipeline = self.pipeline[:]
        if pipeline:
            self.pipeline.extend(pipeline)
        self.config = self.config.copy()
    
    def tail(self, environ, start_response):
        """WSGI application callable for the actual CherryPy application.
        
        You probably shouldn't call this; call self.__call__ instead,
        so that any WSGI middleware in self.pipeline can run first.
        """
        return self.response_class(environ, start_response, self.cpapp)
    
    def __call__(self, environ, start_response):
        head = self.head
        if head is None:
            # Create and nest the WSGI apps in our pipeline (in reverse order).
            # Then memoize the result in self.head.
            head = self.tail
            for name, callable in self.pipeline[::-1]:
                conf = self.config.get(name, {})
                head = callable(head, **conf)
            self.head = head
        return head(environ, start_response)
    
    def namespace_handler(self, k, v):
        """Config handler for the 'wsgi' namespace."""
        if k == "pipeline":
            # Note this allows multiple 'wsgi.pipeline' config entries
            # (but each entry will be processed in a 'random' order).
            # It should also allow developers to set default middleware
            # in code (passed to self.__init__) that deployers can add to
            # (but not remove) via config.
            self.pipeline.extend(v)
        else:
            name, arg = k.split(".", 1)
            bucket = self.config.setdefault(name, {})
            bucket[arg] = v



#                            Server components                            #


class CPHTTPRequest(wsgiserver.HTTPRequest):
    
    def parse_request(self):
        mhs = _cherrypy.server.max_request_header_size
        if mhs > 0:
            self.rfile = _http.SizeCheckWrapper(self.rfile, mhs)
        
        try:
            wsgiserver.HTTPRequest.parse_request(self)
        except _http.MaxSizeExceeded:
            self.simple_response("413 Request Entity Too Large")
            _cherrypy.log(traceback=True)
    
    def decode_chunked(self):
        """Decode the 'chunked' transfer coding."""
        if isinstance(self.rfile, _http.SizeCheckWrapper):
            self.rfile = self.rfile.rfile
        mbs = _cherrypy.server.max_request_body_size
        if mbs > 0:
            self.rfile = _http.SizeCheckWrapper(self.rfile, mbs)
        try:
            return wsgiserver.HTTPRequest.decode_chunked(self)
        except _http.MaxSizeExceeded:
            self.simple_response("413 Request Entity Too Large")
            _cherrypy.log(traceback=True)
            return False


class CPHTTPConnection(wsgiserver.HTTPConnection):
    
    RequestHandlerClass = CPHTTPRequest


class CPWSGIServer(wsgiserver.CherryPyWSGIServer):
    
    """Wrapper for wsgiserver.CherryPyWSGIServer.
    
    wsgiserver has been designed to not reference CherryPy in any way,
    so that it can be used in other frameworks and applications. Therefore,
    we wrap it here, so we can set our own mount points from cherrypy.tree.
    
    """
    
    ConnectionClass = CPHTTPConnection
    
    def __init__(self):
        server = _cherrypy.server
        sockFile = server.socket_file
        if sockFile:
            bind_addr = sockFile
        else:
            bind_addr = (server.socket_host, server.socket_port)
        
        s = wsgiserver.CherryPyWSGIServer
        # We could just pass cherrypy.tree, but by passing tree.apps,
        # we get correct SCRIPT_NAMEs as early as possible.
        s.__init__(self, bind_addr, _cherrypy.tree.apps,
                   server.thread_pool,
                   server.socket_host,
                   request_queue_size = server.socket_queue_size,
                   timeout = server.socket_timeout,
                   shutdown_timeout = server.shutdown_timeout,
                   )
        self.protocol = server.protocol_version
        self.ssl_certificate = server.ssl_certificate
        self.ssl_private_key = server.ssl_private_key

