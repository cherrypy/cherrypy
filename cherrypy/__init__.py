"""Global module that all modules developing with CherryPy should import."""

__version__ = '3.0.0alpha'

import logging as _logging
import os as _os
_localdir = _os.path.dirname(__file__)

from cherrypy._cperror import HTTPError, HTTPRedirect, InternalRedirect, NotFound
from cherrypy._cperror import TimeoutError

from cherrypy import _cptools
tools = _cptools.default_toolbox
Tool = _cptools.Tool

from cherrypy import _cptree
tree = _cptree.Tree()
from cherrypy._cptree import Application
from cherrypy import _cpengine
engine = _cpengine.Engine()
from cherrypy import _cpserver
server = _cpserver.Server()

def quickstart(root, script_name="", conf=None):
    """Mount the given app, start the engine and builtin server, then block."""
    tree.mount(root, script_name, conf)
    server.quickstart()
    engine.start()

try:
    from threading import local as _local
except ImportError:
    from cherrypy._cpthreadinglocal import local as _local

# Create a threadlocal object to hold the request, response, and other
# objects. In this way, we can easily dump those objects when we stop/start
# a new HTTP conversation, yet still refer to them as module-level globals
# in a thread-safe way.
_serving = _local()


class _ThreadLocalProxy(object):
    
    __slots__ = ['__attrname__', '_default_child', '__dict__']
    
    def __init__(self, attrname, default):
        self.__attrname__ = attrname
        self._default_child = default
    
    def _get_child(self):
        try:
            return getattr(_serving, self.__attrname__)
        except AttributeError:
            # Bind dummy instances of default objects to help introspection.
            return self._default_child
    
    def __getattr__(self, name):
        return getattr(self._get_child(), name)
    
    def __setattr__(self, name, value):
        if name in ("__attrname__", "_default_child"):
            object.__setattr__(self, name, value)
        else:
            setattr(self._get_child(), name, value)
    
    def __delattr__(self, name):
        delattr(self._get_child(), name)
    
    def _get_dict(self):
        childobject = self._get_child()
        d = childobject.__class__.__dict__.copy()
        d.update(childobject.__dict__)
        return d
    __dict__ = property(_get_dict)
    
    def __getitem__(self, key):
        return self._get_child()[key]
    
    def __setitem__(self, key, value):
        self._get_child()[key] = value


# Create request and response object (the same objects will be used
#   throughout the entire life of the webserver, but will redirect
#   to the "_serving" object)
from cherrypy.lib import http as _http
request = _ThreadLocalProxy('request',
                            _cprequest.Request(_http.Host("localhost", 80),
                                               _http.Host("localhost", 1111)))
response = _ThreadLocalProxy('response', _cprequest.Response())

# Create thread_data object as a thread-specific all-purpose storage
thread_data = _local()



#                                 Logging                                 #


_error_log = _logging.getLogger("cherrypy.error")
_error_log.setLevel(_logging.DEBUG)
_access_log = _logging.getLogger("cherrypy.access")
_access_log.setLevel(_logging.INFO)


class _LogManager(object):
    
    screen = True
    error_file = _os.path.join(_os.getcwd(), _localdir, "error.log")
    # Using an access file makes CP about 10% slower.
    access_file = ''
    
    def error(self, msg='', context='', severity=_logging.DEBUG, traceback=False):
        """Write to the 'error' log.
        
        This is not just for errors! Applications may call this at any time
        to log application-specific information.
        """
        if traceback:
            from cherrypy import _cperror
            msg += _cperror.format_exc()
        
        try:
            elog = request.app.error_log
        except AttributeError:
            elog = _error_log
        elog.log(severity, ' '.join((self.time(), context, msg)))
    
    def __call__(self, *args, **kwargs):
        return self.error(*args, **kwargs)
    
    def access(self):
        """Write to the access log."""
        tmpl = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'
        s = tmpl % {'h': request.remote.name or request.remote.ip,
                    'l': '-',
                    'u': getattr(request, "login", None) or "-",
                    't': self.time(),
                    'r': request.request_line,
                    's': response.status.split(" ", 1)[0],
                    'b': response.headers.get('Content-Length', '') or "-",
                    'f': request.headers.get('referer', ''),
                    'a': request.headers.get('user-agent', ''),
                    }
        try:
            request.app.access_log.log(_logging.INFO, s)
        except:
            self.error(traceback=True)
    
    def time(self):
        """Return now() in Apache Common Log Format (no timezone)."""
        import datetime, rfc822
        now = datetime.datetime.now()
        month = rfc822._monthnames[now.month - 1].capitalize()
        return ('[%02d/%s/%04d:%02d:%02d:%02d]' %
                (now.day, month, now.year, now.hour, now.minute, now.second))


log = _LogManager()


#                       Helper functions for CP apps                       #


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


# Set up config last so it can wrap other top-level objects
from cherrypy import _cpconfig
config = _cpconfig.Config()
