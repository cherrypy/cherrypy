"""CherryPy tools. A "tool" is any helper, adapted to CP.

Tools are usually designed to be used in a variety of ways (although some
may only offer one if they choose):
    
    Library calls: all tools are callables that can be used wherever needed.
        The arguments are straightforward and should be detailed within the
        docstring.
    
    Function decorators: if the tool exposes a "wrap" callable, that is
        assumed to be a decorator for use in wrapping individual CherryPy
        page handlers (methods on the CherryPy tree). The tool may choose
        not to call the page handler at all, if the response has already
        been populated.
    
    CherryPy hooks: "hooks" are points in the CherryPy request-handling
        process which may hand off control to registered callbacks. The
        Request object possesses a "hooks" attribute (a HookMap)
        for manipulating this. If a tool exposes a "setup" callable,
        it will be called once per Request (if the feature is enabled
        via config).

Tools may be implemented as any object with a namespace. The builtins
are generally either modules or instances of the tools.Tool class.
"""

import cherrypy


class Tool(object):
    """A registered function for use with CherryPy request-processing hooks."""
    
    def __init__(self, point, callable, name=None):
        self.point = point
        self.callable = callable
        self.name = name
        # TODO: add an attribute to self for each arg
        # in inspect.getargspec(callable)
    
    def __call__(self, *args, **kwargs):
        return self.callable(*args, **kwargs)
    
    def merged_args(self, d=None):
        conf = cherrypy.request.toolmap.get(self.name, {}).copy()
        conf.update(d or {})
        if "on" in conf:
            del conf["on"]
        return conf
    
    def wrap(self, *args, **kwargs):
        """Call-time decorator (wrap the handler with pre and post logic).
        
        For example:
        
            @tools.decode.wrap(encoding='chinese')
            def mandarin(self, name):
                return "%s, ni hao shi jie" % name
            mandarin.exposed = True
        """
        def deco(f):
            def wrapper(*a, **kw):
                self.callable(*args, **self.merged_args(kwargs))
                return f(*a, **kw)
            return wrapper
        return deco
    
    def enable(self, **kwargs):
        """Compile-time decorator (turn on the tool in config).
        
        For example:
        
            @tools.base_url.enable()
            def whats_my_base(self):
                return cherrypy.request.base
            whats_my_base.exposed = True
        """
        def wrapper(f):
            if not hasattr(f, "_cp_config"):
                f._cp_config = {}
            f._cp_config["tools." + self.name + ".on"] = True
            for k, v in kwargs:
                f._cp_config["tools." + self.name + "." + k] = v
            return f
        return wrapper
    
    def setup(self):
        """Hook this tool into cherrypy.request.
        
        The standard CherryPy request object will automatically call this
        method when the tool is "turned on" in config.
        """
        conf = self.merged_args()
        cherrypy.request.hooks.attach(self.point, self.callable, conf)


class MainTool(Tool):
    """Tool which is called 'before main', that may skip normal handlers.
    
    The callable provided should return True if processing should skip
    the normal page handler, and False if it should not.
    """
    
    def __init__(self, callable, name=None):
        Tool.__init__(self, 'before_main', callable, name)
    
    def handler(self, *args, **kwargs):
        """Use this tool as a CherryPy page handler.
        
        For example:
            class Root:
                nav = tools.staticdir.handler(section="/nav", dir="nav",
                                              root=absDir)
        """
        def wrapper(*a, **kw):
            handled = self.callable(*args, **self.merged_args(kwargs))
            if not handled:
                raise cherrypy.NotFound()
            return cherrypy.response.body
        wrapper.exposed = True
        return wrapper
    
    def wrap(self, *args, **kwargs):
        """Make a decorator for this tool.
        
        For example:
        
            @tools.staticdir.wrap(section="/slides", dir="styles", root=absDir)
            def slides(self, slide=None, style=None):
                return "No such file"
            slides.exposed = True
        """
        def deco(f):
            def wrapper(*a, **kw):
                handled = self.callable(*args, **self.merged_args(kwargs))
                if handled:
                    return cherrypy.response.body
                else:
                    return f(*a, **kw)
            return wrapper
        return deco
    
    def setup(self):
        """Hook this tool into cherrypy.request.
        
        The standard CherryPy request object will automatically call this
        method when the tool is "turned on" in config.
        """
        def wrapper():
            if self.callable(**self.merged_args()):
                cherrypy.request.handler = None
        # Don't pass conf (or our wrapper will get wrapped!)
        cherrypy.request.hooks.attach(self.point, wrapper)


class ErrorTool(Tool):
    """Tool which is used to replace the default request.error_response."""
    
    def __init__(self, callable, name=None):
        Tool.__init__(self, None, callable, name)
    
    def setup(self):
        """Hook this tool into cherrypy.request.
        
        The standard CherryPy request object will automatically call this
        method when the tool is "turned on" in config.
        """
        def wrapper():
            self.callable(**self.merged_args())
        cherrypy.request.error_response = wrapper


#                              Builtin tools                              #

from cherrypy.lib import cptools, encodings, static
from cherrypy.lib import sessions as _sessions, xmlrpc as _xmlrpc
from cherrypy.lib import caching as _caching, wsgiapp as _wsgiapp


class StaticDirTool(MainTool):
    def setup(self):
        """Hook this tool into cherrypy.request using the given conf."""
        conf = self.merged_args()
        def wrapper():
            if self.callable(**conf):
                cherrypy.request.handler = None
        # Don't pass conf (or our wrapper will get wrapped!)
        cherrypy.request.hooks.attach(self.point, wrapper)


class SessionTool(Tool):
    def __init__(self):
        self.point = "before_finalize"
        self.callable = _sessions.save
        self.name = "sessions"
    
    def wrap(self, **kwargs):
        """Make a decorator for this tool."""
        def deco(f):
            def wrapper(*a, **kw):
                conf = cherrypy.request.toolmap.get(self.name, {}).copy()
                conf.update(kwargs)
                
                s = cherrypy.request._session = _sessions.Session()
                for k, v in conf.iteritems():
                    setattr(s, str(k), v)
                s.init()
                if not hasattr(cherrypy, "session"):
                    cherrypy.session = _sessions.SessionWrapper()
                
                result = f(*a, **kw)
                _sessions.save()
                cherrypy.request.hooks.attach('on_end_request', _sessions.cleanup)
                return result
            return wrapper
        return deco
    
    def setup(self):
        """Hook this tool into cherrypy.request using the given conf.
        
        The standard CherryPy request object will automatically call this
        method when the tool is "turned on" in config.
        """
        def init():
            conf = cherrypy.request.toolmap.get(self.name, {})
            
            s = cherrypy.request._session = _sessions.Session()
            for k, v in conf.iteritems():
                setattr(s, str(k), v)
            s.init()
            
            if not hasattr(cherrypy, "session"):
                cherrypy.session = _sessions.SessionWrapper()
        # init must be bound after headers are read
        cherrypy.request.hooks.attach('before_request_body', init)
        cherrypy.request.hooks.attach('before_finalize', _sessions.save)
        cherrypy.request.hooks.attach('on_end_request', _sessions.cleanup)


class XMLRPCController(object):
    
    _cp_config = {'tools.xmlrpc.on': True}
    
    def __call__(self, *vpath, **params):
        rpcparams, rpcmethod = _xmlrpc.process_body()
        
        subhandler = self
        for attr in str(rpcmethod).split('.'):
            subhandler = getattr(subhandler, attr, None)
            if subhandler is None:
                raise cherrypy.NotFound()
        if not getattr(subhandler, "exposed", False):
            raise cherrypy.NotFound()
        
        body = subhandler(*(vpath + rpcparams), **params)
        conf = cherrypy.request.toolmap.get("xmlrpc", {})
        _xmlrpc.respond(body,
                        conf.get('encoding', 'utf-8'),
                        conf.get('allow_none', 0))
        return cherrypy.response.body
    __call__.exposed = True
    
    index = __call__


class XMLRPCTool(object):
    """Tool for using XMLRPC over HTTP.
    
    Python's None value cannot be used in standard XML-RPC; to allow
    using it via an extension, provide a true value for allow_none.
    """
    
    def setup(self):
        """Hook this tool into cherrypy.request using the given conf."""
        request = cherrypy.request
        if hasattr(request, 'xmlrpc'):
            return
        request.xmlrpc = True
        request.error_response = _xmlrpc.on_error
        path_info = request.path_info
        ppath = _xmlrpc.patched_path(path_info)
        if ppath != path_info:
            raise cherrypy.InternalRedirect(ppath)


class WSGIAppTool(MainTool):
    """A tool for running any WSGI middleware/application within CP.
    
    Here are the parameters:
    
    wsgi_app - any wsgi application callable
    env_update - a dictionary with arbitrary keys and values to be
                 merged with the WSGI environment dictionary.
    
    Example:
    
    class Whatever:
        _cp_config = {'tools.wsgiapp.on': True,
                      'tools.wsgiapp.app': some_app,
                      'tools.wsgiapp.env': app_environ,
                      }
    """
    
    def setup(self):
        # Keep request body intact so the wsgi app can have its way with it.
        cherrypy.request.process_request_body = False
        MainTool.setup(self)


class Toolbox(object):
    """A collection of Tools."""
    
    def __setattr__(self, name, value):
        # If the Tool.name is None, supply it from the attribute name.
        if isinstance(value, Tool):
            if value.name is None:
                value.name = name
        object.__setattr__(self, name, value)


default_toolbox = Toolbox()
default_toolbox.session_auth = MainTool(cptools.session_auth)
default_toolbox.base_url = Tool('before_request_body', cptools.base_url)
default_toolbox.response_headers = Tool('before_finalize', cptools.response_headers)
# We can't call virtual_host in on_start_resource,
# because it's failsafe and the redirect would be swallowed.
default_toolbox.virtual_host = Tool('before_request_body', cptools.virtual_host)
default_toolbox.log_tracebacks = Tool('before_error_response', cptools.log_traceback)
default_toolbox.log_headers = Tool('before_error_response', cptools.log_request_headers)
default_toolbox.err_redirect = ErrorTool(cptools.redirect)
default_toolbox.etags = Tool('before_finalize', cptools.validate_etags)
default_toolbox.decode = Tool('before_main', encodings.decode)
default_toolbox.encode = Tool('before_finalize', encodings.encode)
default_toolbox.gzip = Tool('before_finalize', encodings.gzip)
default_toolbox.staticdir = StaticDirTool(static.staticdir)
default_toolbox.staticfile = MainTool(static.staticfile)
default_toolbox.sessions = SessionTool()
default_toolbox.xmlrpc = XMLRPCTool()
default_toolbox.wsgiapp = WSGIAppTool(_wsgiapp.run)
default_toolbox.caching = _caching


del cptools, encodings, static
