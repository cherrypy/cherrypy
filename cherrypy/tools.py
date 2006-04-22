"""CherryPy tools. A "tool" is any helper, adapted to CP.

Tools are usually designed to be used in a variety of ways (although some
may only offer one if they choose):
    
    Library calls: all tools are callables that can be used wherever needed.
        The arguments are straightforward and should be detailed within the
        docstring.
    
    Function decorators: if the tool exposes a "wrap" callable, that
        is assumed to be a decorator for use in wrapping individual
        CherryPy page handlers (methods on the CherryPy tree).
    
    CherryPy hooks: "hooks" are points in the CherryPy request-handling
        process which may hand off control to registered callbacks. The
        Request object possesses a "hooks" attribute for manipulating
        this. If a tool exposes a "setup" callable, this will be called
        once per Request (if the feature is enabled via config).
    
    WSGI middleware:
        

Tools may be implemented as any object with a namespace. The builtins
are generally either modules or instances of the tools.Tool class.
"""

import cherrypy
from cherrypy.lib import cptools, encodings, static

# These modules are themselves Tools
from cherrypy.lib import caching


class Tool(object):
    
    def __init__(self, point, callable):
        self.point = point
        self.callable = callable
        # TODO: add an attribute to self for each arg
        # in inspect.getargspec(callable)
    
    def __call__(self, *args, **kwargs):
        self.callable(*args, **kwargs)
    
    def wrap(self, f, *args, **kwargs):
        """Decorator for this tool."""
        def wrapper(*a, **kw):
            self.callable(*args, **kwargs)
            f(*a, **kw)
        missing = object()
        exposed = getattr(f, "exposed", missing)
        if exposed is not missing:
            wrapper.exposed = exposed
        return wrapper
    
    def setup(self, conf):
        """Hook this tool into cherrypy.request using the given conf."""
        cherrypy.request.hooks.attach(self.point, self.callable, conf)


class MainTool(Tool):
    """Tool which is called 'before main', that may skip normal handlers.
    
    The callable provided should return True if processing should skip
    the normal page handler, and False if it should not.
    """
    
    def __init__(self, callable):
        self.point = 'before_main'
        self.callable = callable
    
    def __call__(self, *args, **kwargs):
        self.callable(*args, **kwargs)
    
    def wrap(self, f, *args, **kwargs):
        """Decorator for this tool."""
        def wrapper(*a, **kw):
            handled = self.callable(*args, **kwargs)
            if not handled:
                f(*a, **kw)
        missing = object()
        exposed = getattr(f, "exposed", missing)
        if exposed is not missing:
            wrapper.exposed = exposed
        return wrapper
    
    def setup(self, conf):
        """Hook this tool into cherrypy.request using the given conf."""
        def wrapper():
            if self.callable(**conf):
                cherrypy.request.execute_main = False
        # Don't pass conf (or our wrapper will get wrapped!)
        cherrypy.request.hooks.attach(self.point, wrapper)


base_url = Tool('before_request_body', cptools.base_url)
response_headers = Tool('before_finalize', cptools.response_headers)
virtual_host = Tool('before_request_body', cptools.virtual_host)

decode = Tool('before_main', encodings.decode)
encode = Tool('before_finalize', encodings.encode)
gzip = Tool('before_finalize', encodings.gzip)

staticdir = MainTool(static.get_dir)
staticfile = MainTool(static.get_file)

