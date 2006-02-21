"""Create and manage the CherryPy server."""

import threading
import time

import cherrypy
from cherrypy import _cphttptools
from cherrypy.lib import cptools

from cherrypy._cpengine import Engine, STOPPED, STARTING, STARTED

_missing = object()


class Server(Engine):
    
    def __init__(self):
        Engine.__init__(self)
        self._is_setup = False
        self.blocking = True
        
        self.httpserver = None
        # Starting in 2.2, the "httpserverclass" attr is essentially dead;
        # no CP code uses it. Inspect "httpserver" instead.
        self.httpserverclass = None
        
        # Backward compatibility:
        self.onStopServerList = self.on_stop_server_list
        self.onStartThreadList = self.on_start_thread_list
        self.onStartServerList = self.on_start_server_list
        self.onStopThreadList = self.on_stop_thread_list
    
    def start(self, init_only=False, server_class=_missing, server=None, **kwargs):
        """Main function. MUST be called from the main thread.
        
        Set initOnly to True to keep this function from blocking.
        Set serverClass and server to None to skip starting any HTTP server.
        """
        
        # Read old variable names for backward compatibility
        if 'initOnly' in kwargs:
            init_only = kwargs['initOnly']
        if 'serverClass' in kwargs:
            server_class = kwargs['serverClass']
        
        conf = cherrypy.config.get
        if server is None:
            if server_class is _missing:
                server_class = conf("server.class", _missing)
            if server_class is _missing:
                import _cpwsgi
                server_class = _cpwsgi.WSGIServer
            elif server_class and isinstance(server_class, basestring):
                # Dynamically load the class from the given string
                server_class = cptools.attributes(server_class)
            self.httpserverclass = server_class
            if server_class is not None:
                self.httpserver = server_class()
        else:
            self.httpserverclass = server.__class__
            self.httpserver = server
        
        self.blocking = not init_only
        Engine.start(self)
    
    def _start(self):
        if not self._is_setup:
            self.setup()
            self._is_setup = True
        Engine._start(self)
        self.start_http_server()
        if self.blocking:
            self.block()
    
    def restart(self):
        """Restart the application server engine."""
        self.stop()
        self.state = STARTING
        self.interrupt = None
        self._start()
    
    def start_http_server(self, blocking=True):
        """Start the requested HTTP server."""
        if not self.httpserver:
            return
        
        if cherrypy.config.get('server.socket_port'):
            host = cherrypy.config.get('server.socket_host')
            port = cherrypy.config.get('server.socket_port')
            
            wait_for_free_port(host, port)
            
            if not host:
                host = 'localhost'
            on_what = "http://%s:%s/" % (host, port)
        else:
            on_what = "socket file: %s" % cherrypy.config.get('server.socket_file')
        
        # HTTP servers MUST be started in a new thread, so that the
        # main thread persists to receive KeyboardInterrupt's. If an
        # exception is raised in the http server's main thread then it's
        # trapped here, and the CherryPy app server is shut down (via
        # self.interrupt).
        def _start_http():
            try:
                self.httpserver.start()
            except KeyboardInterrupt, exc:
                self.interrupt = exc
                self.stop()
            except SystemExit, exc:
                self.interrupt = exc
                self.stop()
                raise
        t = threading.Thread(target=_start_http)
        t.setName("CPHTTPServer " + t.getName())
        t.start()
        
        if blocking:
            self.wait_for_http_ready()
        
        cherrypy.log("Serving HTTP on %s" % on_what, 'HTTP')
    
    def wait(self):
        """Block the caller until ready to receive requests (or error)."""
        Engine.wait(self)
        self.wait_for_http_ready()
    
    def wait_for_http_ready(self):
        if self.httpserver:
            while not getattr(self.httpserver, "ready", True) and not self.interrupt:
                time.sleep(.1)
            
            # Wait for port to be occupied
            if cherrypy.config.get('server.socket_port'):
                host = cherrypy.config.get('server.socket_host')
                port = cherrypy.config.get('server.socket_port')
                if not host:
                    host = 'localhost'
                
                for trial in xrange(50):
                    if self.interrupt:
                        break
                    try:
                        check_port(host, port)
                    except IOError:
                        break
                    else:
                        time.sleep(.1)
                else:
                    cherrypy.log("Port %s not bound on %s" %
                                 (repr(port), repr(host)), 'HTTP')
                    raise cherrypy.NotReady("Port not bound.")
    
    def stop(self):
        """Stop, including any HTTP servers."""
        self.stop_http_server()
        Engine.stop(self)
    
    def stop_http_server(self):
        """Stop the HTTP server."""
        try:
            httpstop = self.httpserver.stop
        except AttributeError:
            pass
        else:
            # httpstop() MUST block until the server is *truly* stopped.
            httpstop()
            cherrypy.log("HTTP Server shut down", "HTTP")
    
    def start_with_callback(self, func, args=None, kwargs=None,
                            server_class = _missing, serverClass = None):
        """Start, then callback the given func in a new thread."""
        
        # Read old name for backward compatibility
        if serverClass is not None:
            server_class = None
        
        if args is None:
            args = ()
        if kwargs is None:
            kwargs = {}
        args = (func,) + args
        
        def _callback(func, *args, **kwargs):
            self.wait()
            func(*args, **kwargs)
        t = threading.Thread(target=_callback, args=args, kwargs=kwargs)
        t.setName("CPServer Callback " + t.getName())
        t.start()
        
        self.start(server_class = server_class)


def check_port(host, port):
    """Raise an error if the given port is not free on the given host."""
    sock_file = cherrypy.config.get('server.socket_file')
    if sock_file:
        return
    
    if not host:
        host = 'localhost'
    port = int(port)
    
    import socket
    
    # AF_INET or AF_INET6 socket
    # Get the correct address family for our host (allows IPv6 addresses)
    for res in socket.getaddrinfo(host, port, socket.AF_UNSPEC,
                                  socket.SOCK_STREAM):
        af, socktype, proto, canonname, sa = res
        s = None
        try:
            s = socket.socket(af, socktype, proto)
            # See http://groups.google.com/group/cherrypy-users/
            #        browse_frm/thread/bbfe5eb39c904fe0
            s.settimeout(1.0)
            s.connect((host, port))
            s.close()
            raise IOError("Port %s is in use on %s; perhaps the previous "
                          "server did not shut down properly." %
                          (repr(port), repr(host)))
        except socket.error:
            if s:
                s.close()


def wait_for_free_port(host, port):
    """Wait for the specified port to become free (drop requests)."""
    if not host:
        host = 'localhost'
    
    for trial in xrange(50):
        try:
            check_port(host, port)
        except IOError:
            # Give the old server thread time to free the port.
            time.sleep(.1)
        else:
            return
    
    cherrypy.log("Port %s not free on %s" % (repr(port), repr(host)), 'HTTP')
    raise cherrypy.NotReady("Port not free.")

def wait_for_occupied_port(host, port):
    """Wait for the specified port to become active (receive requests)."""
    if not host:
        host = 'localhost'
    
    for trial in xrange(50):
        try:
            check_port(host, port)
        except IOError:
            return
        else:
            time.sleep(.1)
    
    cherrypy.log("Port %s not bound on %s" % (repr(port), repr(host)), 'HTTP')
    raise cherrypy.NotReady("Port not bound.")
