"""Create and manage the CherryPy server."""

import cgi
import sys
import threading
import time
import warnings

import cherrypy
from cherrypy import _cphttptools, filters
from cherrypy.lib import autoreload, profiler, cptools

# Use a flag to indicate the state of the application server.
STOPPED = 0
STARTING = None
STARTED = 1

_missing = object()


class Server(object):
    
    request_class = _cphttptools.Request
    
    def __init__(self):
        self.state = STOPPED
        self.seen_threads = {}
        
        self.httpserver = None
        self.httpserverclass = None
        self.interrupt = None
        
        # Set some special attributes for adding hooks
        self.on_start_server_list = []
        self.on_start_thread_list = []
        self.on_stop_server_list = []
        self.on_stop_thread_list = []

        # Backward compatibility:
        self.onStopServerList = []
        self.onStartThreadList = []
        self.onStartServerList = []
        self.onStopThreadList = []
    
    def start(self, init_only = False, server_class = _missing, **kwargs):
        """Main function. MUST be called from the main thread.
        
        Set initOnly to True to keep this function from blocking.
        Set serverClass to None to skip starting any HTTP server.
        """
        
        # Read old variable names for backward compatibility
        if 'initOnly' in kwargs:
            init_only = kwargs['initOnly']
        if 'serverClass' in kwargs:
            server_class = kwargs['serverClass']
        cherrypy.log("%s %s" % (init_only, server_class))
        
        self.state = STARTING
        self.interrupt = None
        
        conf = cherrypy.config.get
        
        if server_class is _missing:
            server_class = conf("server.class", _missing)
        if server_class is _missing:
            import _cpwsgi
            server_class = _cpwsgi.WSGIServer
        elif server_class and isinstance(server_class, basestring):
            # Dynamically load the class from the given string
            server_class = cptools.attributes(server_class)
        
        self.blocking = not init_only
        self.httpserverclass = server_class
        
        # Hmmm...we *could* check config in _start instead, but I think
        # most people would like CP to fail before autoreload kicks in.
        check_config()
        
        # Autoreload, but check server_class. If None, we're not starting
        # our own webserver, and therefore could do Very Bad Things when
        # autoreload calls sys.exit.
        if server_class is not None:
            if conf('autoreload.on', False):
                try:
                    freq = conf('autoreload.frequency', 1)
                    autoreload.main(self._start, freq=freq)
                except KeyboardInterrupt:
                    cherrypy.log("<Ctrl-C> hit: shutting down autoreloader", "HTTP")
                    self.stop()
                except SystemExit:
                    cherrypy.log("SystemExit raised: shutting down autoreloader", "HTTP")
                    self.stop()
                    # We must raise here: if this is a process spawned by
                    # autoreload, then it must return its error code to
                    # the parent.
                    raise
                return
        
        self._start()
    
    def _start(self):
        # Output config options to log
        if cherrypy.config.get("server.log_config_options", True):
            cherrypy.config.outputConfigMap()
        
        try:
            configure()
            
            for func in cherrypy.server.on_start_server_list + cherrypy.server.onStartServerList:
                func()
            self.start_http_server()
            self.state = STARTED
            
            if self.blocking:
                # Block forever (wait for KeyboardInterrupt or SystemExit).
                while True:
                    time.sleep(.1)
                    if self.interrupt:
                        raise self.interrupt
        except KeyboardInterrupt:
            cherrypy.log("<Ctrl-C> hit: shutting down server", "HTTP")
            self.stop()
        except SystemExit:
            cherrypy.log("SystemExit raised: shutting down server", "HTTP")
            self.stop()
        except:
            # Don't bother logging, since we're going to re-raise.
            self.interrupt = sys.exc_info()[1]
            self.stop()
            raise
    
    def start_http_server(self, blocking=True):
        """Start the requested HTTP server."""
        if self.httpserver is not None:
            msg = ("You seem to have an HTTP server still running."
                   "Please call server.stop_http_server() "
                   "before continuing.")
            warnings.warn(msg)
        
        if self.httpserverclass is None:
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
        
        # Instantiate the server.
        self.httpserver = self.httpserverclass()
        
        # HTTP servers MUST be started in a new thread, so that the
        # main thread persists to receive KeyboardInterrupt's. This
        # wrapper traps an interrupt in the http server's main thread
        # and shutdowns CherryPy.
        def _start_http():
            try:
                self.httpserver.start()
            except (KeyboardInterrupt, SystemExit), exc:
                self.interrupt = exc
        threading.Thread(target=_start_http).start()
        
        if blocking:
            self.wait_for_http_ready()
        
        cherrypy.log("Serving HTTP on %s" % on_what, 'HTTP')
    
    def wait_for_http_ready(self):
        if self.httpserverclass is not None:
            while not getattr(self.httpserver, "ready", True):
                time.sleep(.1)
            
            # Wait for port to be occupied
            if cherrypy.config.get('server.socket_port'):
                host = cherrypy.config.get('server.socket_host')
                port = cherrypy.config.get('server.socket_port')
                wait_for_occupied_port(host, port)
    
    def request(self, clientAddress, remoteHost, scheme="http"):
        """Obtain an HTTP Request object.
        
        clientAddress: the (IP address, port) of the client
        remoteHost: the IP address of the client
        scheme: either "http" or "https"; defaults to "http"
        """
        if self.state == STOPPED:
            raise cherrypy.NotReady("The CherryPy server has stopped.")
        elif self.state == STARTING:
            raise cherrypy.NotReady("The CherryPy server could not start.")
        
        threadID = threading._get_ident()
        if threadID not in self.seen_threads:
            
            if cherrypy.codecoverage:
                from cherrypy.lib import covercp
                covercp.start()
            
            i = len(self.seen_threads) + 1
            self.seen_threads[threadID] = i
            
            for func in self.on_start_thread_list + self.onStartThreadList:
                func(i)
        
        r = self.request_class(clientAddress[0], clientAddress[1],
                              remoteHost, scheme)
        cherrypy.serving.request = r
        cherrypy.serving.response = _cphttptools.Response()
        return r
    
    def stop(self):
        """Stop, including any HTTP servers."""
        self.stop_http_server()
        
        for thread_ident, i in self.seen_threads.iteritems():
            for func in self.on_stop_thread_list + self.onStopThreadList:
                func(i)
        self.seen_threads.clear()
        
        for func in self.on_stop_server_list + self.onStopServerList:
            func()
        
        self.state = STOPPED
        cherrypy.log("CherryPy shut down", "HTTP")
    
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
        
        self.httpserver = None
    
    def restart(self):
        """Restart, including any HTTP servers."""
        self.stop()
        for func in self.on_start_server_list + self.onStartServerList:
            func()
        self.start_http_server()
        self.state = STARTED
    
    def wait(self):
        """Block the caller until ready to receive requests (or error)."""
        while not self.ready:
            time.sleep(.1)
            if self.interrupt:
                # Something went wrong in server.start,
                # possibly in another thread. Stop this thread.
                raise cherrypy.NotReady("The CherryPy server errored", "HTTP")
    
    def _is_ready(self):
        return bool(self.state == STARTED)
    ready = property(_is_ready, doc="Return True if the server is ready to"
                                    " receive requests, False otherwise.")
    
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
        threading.Thread(target=_callback, args=args, kwargs=kwargs).start()
        
        self.start(server_class = server_class)


def check_config():
    err = cherrypy.WrongConfigValue
    for name, section in cherrypy.config.configs.iteritems():
        for k, v in section.iteritems():
            if k == "server.environment":
                if v and v not in cherrypy.config.environments:
                    raise err("'%s' is not a registered environment." % v)


def configure():
    """Perform one-time actions to prepare the CherryPy core."""
    if cherrypy.codecoverage:
        from cherrypy.lib import covercp
        covercp.start()
    
    conf = cherrypy.config.get
    # TODO: config.checkConfigOptions()
    
    # If sessions are stored in files and we
    # use threading, we need a lock on the file
    if (conf('server.thread_pool') > 1
        and conf('session.storage_type') == 'file'):
        cherrypy._sessionFileLock = threading.RLock()
    
    # set cgi.maxlen which will limit the size of POST request bodies
    cgi.maxlen = conf('server.max_request_size')
    
    # Set up the profiler if requested.
    if conf("profiling.on", False):
        ppath = conf("profiling.path", "")
        cherrypy.profiler = profiler.Profiler(ppath)
    else:
        cherrypy.profiler = None
    
    # Initialize the built in filters
    filters.init()


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
        except socket.error, msg:
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
