"""Global module that all modules developing with CherryPy should import."""

__version__ = '3.0.0RC1'

import os as _os
_localdir = _os.path.dirname(__file__)
from urlparse import urljoin as _urljoin

from cherrypy._cperror import HTTPError, HTTPRedirect, InternalRedirect, NotFound, CherryPyException
from cherrypy._cperror import TimeoutError

from cherrypy import _cprequest
from cherrypy import _cpengine
engine = _cpengine.Engine()

from cherrypy import _cptools
tools = _cptools.default_toolbox
Tool = _cptools.Tool

from cherrypy import _cptree
tree = _cptree.Tree()
from cherrypy._cptree import Application
from cherrypy import _cpwsgi as wsgi
from cherrypy import _cpserver
server = _cpserver.Server()

def quickstart(root, script_name="", config=None):
    """Mount the given app, start the engine and builtin server, then block."""
    if config:
        _global_conf_alias.update(config)
    tree.mount(root, script_name, config)
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
    
    def __delitem__(self, key):
        del self._get_child()[key]


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


from cherrypy import _cplogging

class _GlobalLogManager(_cplogging.LogManager):
    
    def __call__(self, *args, **kwargs):
        try:
            log = request.app.log
        except AttributeError:
            log = self
        return log.error(*args, **kwargs)
    
    def access(self):
        try:
            return request.app.log.access()
        except AttributeError:
            return _cplogging.LogManager.access(self)


log = _GlobalLogManager()
# Set a default screen handler on the global log.
log.screen = True
log.error_file = ''
# Using an access file makes CP about 10% slower. Leave off by default.
log.access_file = ''


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
        if alias is None:
            # expose is being called as a decorator "@expose"
            func.exposed = True
            return func
        else:
            # expose is returning a decorator "@expose(alias=...)"
            return expose_

def url(path="", qs="", script_name=None, base=None, relative=False):
    """Create an absolute URL for the given path.
    
    If 'path' starts with a slash ('/'), this will return
        (base + script_name + path + qs).
    If it does not start with a slash, this returns
        (base + script_name [+ request.path_info] + path + qs).
    
    If script_name is None, cherrypy.request will be used
    to find a script_name, if available.
    
    If base is None, cherrypy.request.base will be used (if available).
    Note that you can use cherrypy.tools.proxy to change this.
    
    Finally, note that this function can be used to obtain an absolute URL
    for the current request path (minus the querystring) by passing no args.
    If you call url(qs=cherrypy.request.query_string), you should get the
    original browser URL (assuming no Internal redirections).
    
    If relative is False (the default), the output will be an absolute URL
    (usually including the scheme, host, vhost, and script_name).
    If relative is True, the output will instead be a URL that is relative
    to the current request path, perhaps including '..' atoms.
    """
    if qs:
        qs = '?' + qs
    
    if request.app:
        if path[:1] != "/":
            # Append/remove trailing slash from path_info as needed
            # (this is to support mistyped URL's without redirecting;
            # if you want to redirect, use tools.trailing_slash).
            pi = request.path_info
            if request.is_index is True:
                if pi[-1:] != '/':
                    pi = pi + '/'
            elif request.is_index is False:
                if pi[-1:] == '/' and pi != '/':
                    pi = pi[:-1]
            
            if path == "":
                path = pi
            else:
                path = _urljoin(pi, path)
        
        if script_name is None:
            script_name = request.app.script_name
        if base is None:
            base = request.base
        
        newurl = base + script_name + path + qs
    else:
        # No request.app (we're being called outside a request).
        # We'll have to guess the base from server.* attributes.
        # This will produce very different results from the above
        # if you're using vhosts or tools.proxy.
        if base is None:
            f = server.socket_file
            if f:
                base = f
            else:
                host = server.socket_host
                if not host:
                    import socket
                    host = socket.gethostname()
                port = server.socket_port
                if server.ssl_certificate:
                    scheme = "https"
                    if port != 443:
                        host += ":%s" % port
                else:
                    scheme = "http"
                    if port != 80:
                        host += ":%s" % port
                base = "%s://%s" % (scheme, host)
        path = (script_name or "") + path
        newurl = base + path + qs
    
    if './' in newurl:
        # Normalize the URL by removing ./ and ../
        atoms = []
        for atom in newurl.split('/'):
            if atom == '.':
                pass
            elif atom == '..':
                atoms.pop()
            else:
                atoms.append(atom)
        newurl = '/'.join(atoms)
    
    if relative:
        old = url().split('/')[:-1]
        new = newurl.split('/')
        while old and new:
            a, b = old[0], new[0]
            if a != b:
                break
            old.pop(0)
            new.pop(0)
        new = (['..'] * len(old)) + new
        newurl = '/'.join(new)
    
    return newurl


# import _cpconfig last so it can reference other top-level objects
from cherrypy import _cpconfig
# Use _global_conf_alias so quickstart can use 'config' as an arg
# without shadowing cherrypy.config.
config = _global_conf_alias = _cpconfig.Config()
