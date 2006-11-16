"""CherryPy tools. A "tool" is any helper, adapted to CP.

Tools are usually designed to be used in a variety of ways (although some
may only offer one if they choose):
    
    Library calls:
        All tools are callables that can be used wherever needed.
        The arguments are straightforward and should be detailed within the
        docstring.
    
    Function decorators:
        All tools, when called, may be used as decorators which configure
        individual CherryPy page handlers (methods on the CherryPy tree).
        That is, "@tools.anytool()" should "turn on" the tool via the
        decorated function's _cp_config attribute.
    
    CherryPy config:
        Hookpoints are places in the CherryPy request-handling process
        which may hand off control to registered callbacks. The Request
        object possesses a "hooks" attribute (a HookMap) for manipulating
        this. If a tool exposes a "_setup" callable, it will be called
        once per Request (if the feature is "turned on" via config).

Tools may be implemented as any object with a namespace. The builtins
are generally either modules or instances of the tools.Tool class.
"""

import cherrypy


class Tool(object):
    """A registered function for use with CherryPy request-processing hooks.
    
    help(tool.callable) should give you more information about this Tool.
    """
    
    namespace = "tools"
    
    def __init__(self, point, callable, name=None, priority=50):
        self._point = point
        self.callable = callable
        self._name = name
        self._priority = priority
        self.__doc__ = self.callable.__doc__
        self._setargs()
    
    def _setargs(self):
        """Copy func parameter names to obj attributes."""
        try:
            import inspect
            for arg in inspect.getargspec(self.callable)[0]:
                setattr(self, arg, None)
        except (ImportError, AttributeError):
            pass
    
    def _merged_args(self, d=None):
        tm = cherrypy.request.toolmaps[self.namespace]
        if self._name in tm:
            conf = tm[self._name].copy()
        else:
            conf = {}
        if d:
            conf.update(d)
        if "on" in conf:
            del conf["on"]
        return conf
    
    def __call__(self, *args, **kwargs):
        """Compile-time decorator (turn on the tool in config).
        
        For example:
        
            @tools.proxy()
            def whats_my_base(self):
                return cherrypy.request.base
            whats_my_base.exposed = True
        """
        if args:
            raise TypeError("The %r Tool does not accept positional "
                            "arguments; you must use keyword arguments."
                            % self._name)
        def tool_decorator(f):
            if not hasattr(f, "_cp_config"):
                f._cp_config = {}
            subspace = self.namespace + "." + self._name + "."
            f._cp_config[subspace + "on"] = True
            for k, v in kwargs.iteritems():
                f._cp_config[subspace + k] = v
            return f
        return tool_decorator
    
    def _setup(self):
        """Hook this tool into cherrypy.request.
        
        The standard CherryPy request object will automatically call this
        method when the tool is "turned on" in config.
        """
        p = getattr(self.callable, "priority", self._priority)
        cherrypy.request.hooks.attach(self._point, self.callable,
                                      priority=p, **self._merged_args())


class HandlerTool(Tool):
    """Tool which is called 'before main', that may skip normal handlers.
    
    The callable provided should return True if processing should skip
    the normal page handler, and False if it should not.
    """
    
    def __init__(self, callable, name=None):
        Tool.__init__(self, 'before_handler', callable, name)
    
    def handler(self, *args, **kwargs):
        """Use this tool as a CherryPy page handler.
        
        For example:
            class Root:
                nav = tools.staticdir.handler(section="/nav", dir="nav",
                                              root=absDir)
        """
        def handle_func(*a, **kw):
            handled = self.callable(*args, **self._merged_args(kwargs))
            if not handled:
                raise cherrypy.NotFound()
            return cherrypy.response.body
        handle_func.exposed = True
        return handle_func
    
    def _wrapper(self, **kwargs):
        if self.callable(**kwargs):
            cherrypy.request.handler = None
    
    def _setup(self):
        """Hook this tool into cherrypy.request.
        
        The standard CherryPy request object will automatically call this
        method when the tool is "turned on" in config.
        """
        p = getattr(self.callable, "priority", self._priority)
        cherrypy.request.hooks.attach(self._point, self._wrapper,
                                      priority=p, **self._merged_args())


class ErrorTool(Tool):
    """Tool which is used to replace the default request.error_response."""
    
    def __init__(self, callable, name=None):
        Tool.__init__(self, None, callable, name)
    
    def _wrapper(self):
        self.callable(**self._merged_args())
    
    def _setup(self):
        """Hook this tool into cherrypy.request.
        
        The standard CherryPy request object will automatically call this
        method when the tool is "turned on" in config.
        """
        cherrypy.request.error_response = self._wrapper


#                              Builtin tools                              #

from cherrypy.lib import cptools, encoding, auth, static, tidy
from cherrypy.lib import sessions as _sessions, xmlrpc as _xmlrpc
from cherrypy.lib import caching as _caching, wsgiapp as _wsgiapp


class SessionTool(Tool):
    """Session Tool for CherryPy."""
    
    def _setup(self):
        """Hook this tool into cherrypy.request.
        
        The standard CherryPy request object will automatically call this
        method when the tool is "turned on" in config.
        """
        Tool._setup(self)
        cherrypy.request.hooks.attach('before_finalize', _sessions.save)
        cherrypy.request.hooks.attach('on_end_request', _sessions.close)


class XMLRPCController(object):
    
    # Note we're hard-coding this into the 'tools' namespace. We could do
    # a huge amount of work to make it relocatable, but the only reason why
    # would be if someone actually disabled the default_toolbox. Meh.
    _cp_config = {'tools.xmlrpc.on': True}
    
    def __call__(self, *vpath, **params):
        rpcparams, rpcmethod = _xmlrpc.process_body()
        
        subhandler = self
        for attr in str(rpcmethod).split('.'):
            subhandler = getattr(subhandler, attr, None)
         
        if subhandler and getattr(subhandler, "exposed", False):
            body = subhandler(*(vpath + rpcparams), **params)
        
        else:
            # http://www.cherrypy.org/ticket/533
            # if a method is not found, an xmlrpclib.Fault should be returned
            # raising an exception here will do that; see
            # cherrypy.lib.xmlrpc.on_error
            raise Exception, 'method "%s" is not supported' % attr
        
        conf = cherrypy.request.toolmaps['tools'].get("xmlrpc", {})
        _xmlrpc.respond(body,
                        conf.get('encoding', 'utf-8'),
                        conf.get('allow_none', 0))
        return cherrypy.response.body
    __call__.exposed = True
    
    index = __call__


class WSGIAppTool(HandlerTool):
    """A tool for running any WSGI middleware/application within CP.
    
    Here are the parameters:
    
    wsgi_app - any wsgi application callable
    env_update - a dictionary with arbitrary keys and values to be
                 merged with the WSGI environ dictionary.
    
    Example:
    
    class Whatever:
        _cp_config = {'tools.wsgiapp.on': True,
                      'tools.wsgiapp.app': some_app,
                      'tools.wsgiapp.env': app_environ,
                      }
    """
    
    def _setup(self):
        # Keep request body intact so the wsgi app can have its way with it.
        cherrypy.request.process_request_body = False
        HandlerTool._setup(self)


class SessionAuthTool(HandlerTool):
    
    def _setargs(self):
        for name in dir(cptools.SessionAuth):
            if not name.startswith("__"):
                setattr(self, name, None)


class CachingTool(Tool):
    """Caching Tool for CherryPy."""
    
    def _wrapper(self, **kwargs):
        request = cherrypy.request
        if _caching.get(**kwargs):
            request.handler = None
        else:
            # Note the devious technique here of adding hooks on the fly
            request.hooks.attach('before_finalize', _caching.tee_output,
                                 priority = 90)
    _wrapper.priority = 20
    
    def _setup(self):
        """Hook caching into cherrypy.request."""
        conf = self._merged_args()
        cherrypy.request.hooks.attach('before_handler', self._wrapper, **conf)



class Toolbox(object):
    """A collection of Tools.
    
    This object also functions as a config namespace handler for itself.
    """
    
    def __init__(self, namespace):
        self.namespace = namespace
        cherrypy.engine.request_class.namespaces[namespace] = self
    
    def __setattr__(self, name, value):
        # If the Tool._name is None, supply it from the attribute name.
        if isinstance(value, Tool):
            if value._name is None:
                value._name = name
            value.namespace = self.namespace
        object.__setattr__(self, name, value)
    
    def __enter__(self):
        cherrypy.request.toolmaps[self.namespace] = {}
        return self
    
    def __call__(self, k, v):
        """Populate request.toolmaps from tools specified in config."""
        toolname, arg = k.split(".", 1)
        map = cherrypy.request.toolmaps[self.namespace]
        bucket = map.setdefault(toolname, {})
        bucket[arg] = v
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Run tool._setup() for each tool in our toolmap."""
        map = cherrypy.request.toolmaps.get(self.namespace)
        if map:
            for name, settings in map.items():
                if settings.get("on", False):
                    tool = getattr(self, name)
                    tool._setup()


default_toolbox = _d = Toolbox("tools")
_d.session_auth = SessionAuthTool(cptools.session_auth)
_d.proxy = Tool('before_request_body', cptools.proxy, priority=30)
_d.response_headers = Tool('on_start_resource', cptools.response_headers)
_d.log_tracebacks = Tool('before_error_response', cptools.log_traceback)
_d.log_headers = Tool('before_error_response', cptools.log_request_headers)
_d.err_redirect = ErrorTool(cptools.redirect)
_d.etags = Tool('before_finalize', cptools.validate_etags)
_d.decode = Tool('before_handler', encoding.decode)
# the order of encoding, gzip, caching is important
_d.encode = Tool('before_finalize', encoding.encode, priority=70)
_d.gzip = Tool('before_finalize', encoding.gzip, priority=80)
_d.staticdir = HandlerTool(static.staticdir)
_d.staticfile = HandlerTool(static.staticfile)
# _sessions.init must be bound after headers are read
_d.sessions = SessionTool('before_request_body', _sessions.init)
_d.xmlrpc = ErrorTool(_xmlrpc.on_error)
_d.wsgiapp = WSGIAppTool(_wsgiapp.run)
_d.caching = CachingTool('before_handler', _caching.get, 'caching')
_d.expires = Tool('before_finalize', _caching.expires)
_d.tidy = Tool('before_finalize', tidy.tidy)
_d.nsgmls = Tool('before_finalize', tidy.nsgmls)
_d.ignore_headers = Tool('before_request_body', cptools.ignore_headers)
_d.referer = Tool('before_request_body', cptools.referer)
_d.basic_auth = Tool('on_start_resource', auth.basic_auth)
_d.digest_auth = Tool('on_start_resource', auth.digest_auth)
_d.trailing_slash = Tool('before_handler', cptools.trailing_slash)
_d.flatten = Tool('before_finalize', cptools.flatten)
_d.accept = Tool('on_start_resource', cptools.accept)

del _d, cptools, encoding, auth, static, tidy
