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
        Request object possesses a "hooks" attribute (a tools.HookMap)
        for manipulating this. If a tool exposes a "setup" callable,
        it will be called once per Request (if the feature is enabled
        via config).

Tools may be implemented as any object with a namespace. The builtins
are generally either modules or instances of the tools.Tool class.
"""

import cherrypy
from cherrypy import _cputil


class HookMap(object):
    
    def __init__(self, points=None, failsafe=None):
        points = points or []
        self.callbacks = dict([(point, []) for point in points])
        self.failsafe = failsafe or []
    
    def attach(self, point, callback, conf=None):
        if conf is None:
            self.callbacks[point].append(callback)
        else:
            def wrapper():
                callback(**conf)
            self.callbacks[point].append(wrapper)
    
    def setup(self):
        """Run tool.setup(conf) for each tool specified in current config."""
        g = globals()
        for toolname, conf in tool_config().iteritems():
            if conf.get("on", False):
                del conf["on"]
                g[toolname].setup(conf)
        
        # Run _cp_setup functions
        mounted_app_roots = cherrypy.tree.mount_points.values()
        objectList = _cputil.get_object_trail()
        objectList.reverse()
        for objname, obj in objectList:
            s = getattr(obj, "_cp_setup", None)
            if s:
                s()
            if obj in mounted_app_roots:
                break
    
    def run(self, point, *args, **kwargs):
        """Execute all registered callbacks for the given point."""
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
                    callback(*args, **kwargs)
                except (KeyboardInterrupt, SystemExit):
                    raise
                except:
                    cherrypy.log(traceback=True)
            else:
                callback(*args, **kwargs)

def tool_config():
    """Return all 'tools.*' config entries as a {toolname: {k: v}} dict."""
    toolmap = {}
    for k, v in cherrypy.config.current_config().iteritems():
        atoms = k.split(".")
        namespace = atoms.pop(0)
        if namespace == "tools":
            toolname = atoms.pop(0)
            bucket = toolmap.setdefault(toolname, {})
            bucket[".".join(atoms)] = v
    return toolmap

def merged_config(toolname, d):
    """Merge arguments from tool config into another dict."""
    mergedkw = d.copy()
    mergedkw.update(tool_config().get(toolname, {}))
    if "on" in mergedkw:
        del mergedkw["on"]
    return mergedkw


class Tool(object):
    
    def __init__(self, point, callable, name=None):
        self.point = point
        self.callable = callable
        if name is None:
            name = callable.__name__
        self.name = name
        # TODO: add an attribute to self for each arg
        # in inspect.getargspec(callable)
        
        class ToolMixin(object):
            def _cp_setup(me):
                self.setup(None)
        self.Mixin = ToolMixin
    
    def __call__(self, *args, **kwargs):
        return self.callable(*args, **kwargs)
    
    def wrap(self, *args, **kwargs):
        """Make a decorator for this tool.
        
        For example:
        
            @tools.decode.wrap(encoding='chinese')
            def mandarin(self, name):
                return "%s, ni hao shi jie" % name
            mandarin.exposed = True
        """
        def deco(f):
            def wrapper(*a, **kw):
                handled = self.callable(*args, **merged_config(self.name, kwargs))
                return f(*a, **kw)
            return wrapper
        return deco
    
    def setup(self, conf):
        """Hook this tool into cherrypy.request using the given conf.
        
        The standard CherryPy request object will automatically call this
        method when the tool is "turned on" in config.
        """
        cherrypy.request.hooks.attach(self.point, self.callable, conf)


class MainTool(Tool):
    """Tool which is called 'before main', that may skip normal handlers.
    
    The callable provided should return True if processing should skip
    the normal page handler, and False if it should not.
    """
    
    def __init__(self, callable, name=None):
        self.point = 'before_main'
        self.callable = callable
        if name is None:
            name = callable.__name__
        self.name = name
    
    def handler(self, *args, **kwargs):
        """Use this tool as a CherryPy page handler.
        
        For example:
            cherrypy.root.nav = tools.staticdir.handler(
                                    section="/nav", dir="nav", root=absDir)
        """
        def wrapper(*a, **kw):
            handled = self.callable(*args, **merged_config(self.name, kwargs))
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
                handled = self.callable(*args, **merged_config(self.name, kwargs))
                if handled:
                    return cherrypy.response.body
                else:
                    return f(*a, **kw)
            return wrapper
        return deco
    
    def setup(self, conf):
        """Hook this tool into cherrypy.request using the given conf.
        
        The standard CherryPy request object will automatically call this
        method when the tool is "turned on" in config.
        """
        def wrapper():
            if self.callable(**conf):
                cherrypy.request.dispatch = None
        # Don't pass conf (or our wrapper will get wrapped!)
        cherrypy.request.hooks.attach(self.point, wrapper)


#                              Builtin tools                              #

from cherrypy.lib import cptools
session_auth = MainTool(cptools.session_auth)
base_url = Tool('before_request_body', cptools.base_url)
response_headers = Tool('before_finalize', cptools.response_headers)
virtual_host = Tool('before_request_body', cptools.virtual_host)
del cptools

from cherrypy.lib import encodings
decode = Tool('before_main', encodings.decode)
encode = Tool('before_finalize', encodings.encode)
gzip = Tool('before_finalize', encodings.gzip)
del encodings

from cherrypy.lib import static
class _StaticDirTool(MainTool):
    def setup(self, conf):
        """Hook this tool into cherrypy.request using the given conf."""
        # Stick the section where "dir" was defined into the params
        conf['section'] = cherrypy.config.get('tools.staticdir.dir',
                                              return_section=True)
        def wrapper():
            if self.callable(**conf):
                cherrypy.request.dispatch = None
        # Don't pass conf (or our wrapper will get wrapped!)
        cherrypy.request.hooks.attach(self.point, wrapper)
staticdir = _StaticDirTool(static.staticdir)
staticfile = MainTool(static.staticfile)
del static

from cherrypy.lib import sessions as _sessions
class _SessionTool(Tool):
    def __init__(self):
        self.point = "before_finalize"
        self.callable = _sessions.save
        self.name = "sessions"
    
    def wrap(self, **kwargs):
        """Make a decorator for this tool."""
        def deco(f):
            def wrapper(*a, **kw):
                s = cherrypy.request._session = _sessions.Session()
                for k, v in merged_config(self.name, kwargs).iteritems():
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
    
    def setup(self, conf):
        """Hook this tool into cherrypy.request using the given conf.
        
        The standard CherryPy request object will automatically call this
        method when the tool is "turned on" in config.
        """
        def init():
            s = cherrypy.request._session = _sessions.Session()
            for k, v in conf.iteritems():
                setattr(s, str(k), v)
            s.init()
            
            if not hasattr(cherrypy, "session"):
                cherrypy.session = _sessions.SessionWrapper()
        cherrypy.request.hooks.attach('before_request_body', init)
        
        cherrypy.request.hooks.attach('before_finalize', _sessions.save)
        cherrypy.request.hooks.attach('on_end_request', _sessions.cleanup)
sessions = _SessionTool()

from cherrypy.lib import xmlrpc as _xmlrpc
class _XMLRPCTool(object):
    """Tool for using XMLRPC over HTTP.
    
    Python's None value cannot be used in standard XML-RPC; to allow
    using it via an extension, provide a true value for allow_none.
    """
    
    def dispatch(self, path):
        """Use this tool for cherrypy.request dispatch.
        
        For example:
            [/rpc]
            dispatch = tools.xmlrpc.dispatch
        """
        request = cherrypy.request
        request.hooks.attach('after_error_response', _xmlrpc.wrap_error)
        
        rpcparams, rpcmethod = _xmlrpc.process_body()
        path = _xmlrpc.patched_path(path, rpcmethod)
        
        from cherrypy import _cprequest
        handler, opath, vpath = _cprequest.find_handler(path)
        
        # Decode any leftover %2F in the virtual_path atoms.
        vpath = tuple([x.replace("%2F", "/") for x in vpath])
        
        body = handler(*(vpath + rpcparams), **request.params)
        conf = tool_config().get("xmlrpc", {})
        _xmlrpc.respond(body,
                        conf.get('encoding', 'utf-8'),
                        conf.get('allow_none', 0))
    
    def setup(self, conf):
        """Hook this tool into cherrypy.request using the given conf."""
        cherrypy.request.dispatch = self.dispatch
xmlrpc = _XMLRPCTool()


# These modules are themselves Tools
from cherrypy.lib import caching
