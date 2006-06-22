"""Global module that all modules developing with CherryPy should import."""

__version__ = '3.0.0alpha'

import logging

from _cperror import HTTPError, HTTPRedirect, InternalRedirect, NotFound, WrongConfigValue
import config

import _cptools
tools = _cptools.default_toolbox

import _cptree
tree = _cptree.Tree()
import _cpengine
engine = _cpengine.Engine()
import _cpserver
server = _cpserver.Server()

def quickstart(root, script_name="", conf=None):
    """Mount the given app, start the engine and builtin server, then block."""
    tree.mount(root, script_name, conf)
    server.start()
    engine.start()

try:
    from threading import local as _local
except ImportError:
    from cherrypy._cpthreadinglocal import local as _local

# Create a threadlocal object to hold the request, response, and other
# objects. In this way, we can easily dump those objects when we stop/start
# a new HTTP conversation, yet still refer to them as module-level globals
# in a thread-safe way.
serving = _local()

# Bind dummy instances of default request/response
# (in the main thread only!) to help introspection.
serving.request = _cprequest.Request("localhost", "11111", "localhost")
serving.response = _cprequest.Response()


class _ThreadLocalProxy(object):
    
    __slots__ = ['__attrname__', '__dict__']
    
    def __init__(self, attrname):
        self.__attrname__ = attrname
    
    def __getattr__(self, name):
        childobject = getattr(serving, self.__attrname__)
        return getattr(childobject, name)
    
    def __setattr__(self, name, value):
        if name == "__attrname__":
            object.__setattr__(self, "__attrname__", value)
        else:
            childobject = getattr(serving, self.__attrname__)
            setattr(childobject, name, value)
    
    def __delattr__(self, name):
        childobject = getattr(serving, self.__attrname__)
        delattr(childobject, name)
    
    def _get_dict(self):
        childobject = getattr(serving, self.__attrname__)
        d = childobject.__class__.__dict__.copy()
        d.update(childobject.__dict__)
        return d
    __dict__ = property(_get_dict)


# Create request and response object (the same objects will be used
#   throughout the entire life of the webserver, but will redirect
#   to the "serving" object)
request = _ThreadLocalProxy('request')
response = _ThreadLocalProxy('response')

# Create thread_data object as a thread-specific all-purpose storage
thread_data = _local()



#                                 Logging                                 #


def logtime():
    import datetime
    now = datetime.datetime.now()
    from cherrypy.lib import http
    month = http.monthname[now.month][:3].capitalize()
    return '%02d/%s/%04d:%02d:%02d:%02d' % (
        now.day, month, now.year, now.hour, now.minute, now.second)

_logfmt = logging.Formatter("%(message)s")

_access_log = logging.getLogger("cherrypy.access")
_access_log.setLevel(logging.INFO)

def _add_access_log_handler(handler):
    if handler.level == logging.NOTSET:
        handler.setLevel(logging.INFO)
    if handler.formatter is None:
        handler.setFormatter(_logfmt)
    _access_log.addHandler(handler)

def log_access():
    """Default method for logging access"""
    tmpl = '%(h)s %(l)s %(u)s [%(t)s] "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'
    s = tmpl % {'h': request.remote_host,
                'l': '-',
                'u': getattr(request, "login", None) or "-",
                't': logtime(),
                'r': request.request_line,
                's': response.status.split(" ", 1)[0],
                'b': response.headers.get('Content-Length', '') or "-",
                'f': request.headers.get('referer', ''),
                'a': request.headers.get('user-agent', ''),
                }
        
    # Create handlers if needed
    if not _access_log.handlers:
        if config.get('server.log_to_screen'):
            _add_access_log_handler(logging.StreamHandler(sys.stdout))
        fname = config.get('log_access_file', '')
        if fname:
            _add_access_log_handler(logging.FileHandler(fname))
    
    _access_log.log(logging.INFO, s)


_error_log = logging.getLogger("cherrypy.error")
_error_log.setLevel(logging.DEBUG)

def _add_error_log_handler(handler):
    if handler.level == logging.NOTSET:
        handler.setLevel(logging.DEBUG)
    if handler.formatter is None:
        handler.setFormatter(_logfmt)
    _error_log.addHandler(handler)

def _log_message(msg, context = '', severity = logging.DEBUG):
    """Default method for logging messages (error log).
    
    This is not just for errors! Applications may call this at any time to
    log application-specific information.
    """
    
    # Create handlers if needed
    if not _error_log.handlers:
        if config.get('server.log_to_screen'):
            _add_error_log_handler(logging.StreamHandler(sys.stdout))
        fname = config.get('log_file', '')
        if fname:
            _add_error_log_handler(logging.FileHandler(fname))
    
    _error_log.log(severity, ' '.join((logtime(), context, msg)))

def log(msg='', context='', severity=logging.DEBUG, traceback=False):
    """Syntactic sugar for writing to the (error) log.
    
    This is not just for errors! Applications may call this at any time to
    log application-specific information.
    """
    if traceback:
        import _cperror
        msg += _cperror.format_exc()
    logfunc = config.get('log_function', _log_message)
    logfunc(msg, context, severity)



#                       Helper functions for CP apps                       #


def decorate(func, decorator):
    """
    Return the decorated func. This will automatically copy all
    non-standard attributes (like exposed) to the newly decorated function.
    """
    newfunc = decorator(func)
    for key in dir(func):
        if not hasattr(newfunc, key):
            setattr(newfunc, key, getattr(func, key))
    return newfunc

def decorateAll(obj, decorator):
    """
    Recursively decorate all exposed functions of obj and all of its children,
    grandchildren, etc. If you used to use aspects, you might want to look
    into these. This function modifies obj; there is no return value.
    """
    obj_type = type(obj)
    for key in dir(obj):
        if hasattr(obj_type, key): # only deal with user-defined attributes
            continue
        value = getattr(obj, key)
        if callable(value) and getattr(value, "exposed", False):
            setattr(obj, key, decorate(value, decorator))
        decorateAll(value, decorator)


class ExposeItems:
    """
    Utility class that exposes a getitem-aware object. It does not provide
    index() or default() methods, and it does not expose the individual item
    objects - just the list or dict that contains them. User-specific index()
    and default() methods can be implemented by inheriting from this class.
    
    Use case:
    
    from cherrypy import ExposeItems
    ...
    root.foo = ExposeItems(mylist)
    root.bar = ExposeItems(mydict)
    """
    exposed = True
    def __init__(self, items):
        self.items = items
    def __getattr__(self, key):
        return self.items[key]


def expose(func=None, alias=None):
    """Expose the function, optionally providing an alias or set of aliases."""
    
    def expose_(func):
        func.exposed = True
        if alias is not None:
            if isinstance(alias, basestring):
                parents[alias.replace(".", "_")] = func
            else:
                for a in alias:
                    parents[a.replace(".", "_")] = func
        return func
    
    import sys, types
    parents = sys._getframe(1).f_locals
    if isinstance(func, (types.FunctionType, types.MethodType)):
        # expose is being called directly, before the method has been bound
        return expose_(func)
    else:
        # expose is being called as a decorator
        if alias is None:
            alias = func
        return expose_

def set_config(**kwargs):
    """Decorator to set _cp_config using the given kwargs."""
    def wrapper(f):
        if not hasattr(f, "_cp_config"):
            f._cp_config = {}
        f._cp_config.update(kwargs)
        return f
    return wrapper

