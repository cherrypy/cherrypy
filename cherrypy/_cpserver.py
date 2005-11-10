"""Create and manage the CherryPy server."""

import cgi
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

seen_threads = {}

_missing = object()


class Server(object):
    
    def __init__(self):
        self.state = STOPPED
        
        self.httpserver = None
        self.httpserverclass = None
        self.interrupt = None
        
        # Set some special attributes for adding hooks
        self.onStartServerList = []
        self.onStartThreadList = []
        self.onStopServerList = []
        self.onStopThreadList = []
    
    def start(self, initOnly=False, serverClass=_missing):
        """Main function. MUST be called from the main thread.
        
        Set initOnly to True to keep this function from blocking.
        Set serverClass to None to skip starting any HTTP server.
        """
        self.state = STARTING
        self.interrupt = None
        
        conf = cherrypy.config.get
        
        if serverClass is _missing:
            serverClass = conf("server.class", _missing)
        if serverClass is _missing:
            import _cpwsgi
            serverClass = _cpwsgi.WSGIServer
        elif serverClass and isinstance(serverClass, basestring):
            # Dynamically load the class from the given string
            serverClass = cptools.attributes(serverClass)
        
        self.blocking = not initOnly
        self.httpserverclass = serverClass
        
        # Autoreload, but check serverClass. If None, we're not starting
        # our own webserver, and therefore could do Very Bad Things when
        # autoreload calls sys.exit.
        if serverClass is not None:
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
        if cherrypy.config.get("server.logConfigOptions", True):
            cherrypy.config.outputConfigMap()
        
        try:
            configure()
            
            for func in cherrypy.server.onStartServerList:
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
    
    def start_http_server(self, blocking=True):
        """Start the requested HTTP server."""
        if self.httpserver is not None:
            msg = ("You seem to have an HTTP server still running."
                   "Please call server.stop_http_server() "
                   "before continuing.")
            warnings.warn(msg)
        
        if self.httpserverclass is None:
            return
        
        if cherrypy.config.get('server.socketPort'):
            host = cherrypy.config.get('server.socketHost')
            port = cherrypy.config.get('server.socketPort')
            
            wait_for_free_port(host, port)
            
            if not host:
                host = 'localhost'
            onWhat = "http://%s:%s/" % (host, port)
        else:
            onWhat = "socket file: %s" % cherrypy.config.get('server.socketFile')
        
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
        
        cherrypy.log("Serving HTTP on %s" % onWhat, 'HTTP')
    
    def wait_for_http_ready(self):
        if self.httpserverclass is not None:
            while not getattr(self.httpserver, "ready", True):
                time.sleep(.1)
            
            # Wait for port to be occupied
            if cherrypy.config.get('server.socketPort'):
                host = cherrypy.config.get('server.socketHost')
                port = cherrypy.config.get('server.socketPort')
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
        if threadID not in seen_threads:
            
            if cherrypy.codecoverage:
                from cherrypy.lib import covercp
                covercp.start()
            
            i = len(seen_threads) + 1
            seen_threads[threadID] = i
            
            for func in self.onStartThreadList:
                func(i)
        
        r = _cphttptools.Request(clientAddress[0], clientAddress[1],
                                 remoteHost, scheme)
        cherrypy.serving.request = r
        cherrypy.serving.response = _cphttptools.Response()
        return r
    
    def stop(self):
        """Stop, including any HTTP servers."""
        self.stop_http_server()
        
        for thread_ident, i in seen_threads.iteritems():
            for func in self.onStopThreadList:
                func(i)
        seen_threads.clear()
        
        for func in self.onStopServerList:
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
        for func in self.onStartServerList:
            func()
        self.start_http_server()
        self.state = STARTED
    
    def wait(self):
        """Block the caller until ready to receive requests."""
        while not self.ready:
            time.sleep(.1)
    
    def _is_ready(self):
        return bool(self.state == STARTED)
    ready = property(_is_ready, doc="Return True if the server is ready to receive requests, False otherwise.")
    
    def start_with_callback(self, func, args=None, kwargs=None,
                            serverClass=_missing):
        """Start, then callback the given func in a new thread."""
        if args is None:
            args = ()
        if kwargs is None:
            kwargs = {}
        args = (func,) + args
        
        def _callback(func, *args, **kwargs):
            self.wait()
            func(*args, **kwargs)
        threading.Thread(target=_callback, args=args, kwargs=kwargs).start()
        
        self.start(serverClass=serverClass)


def configure():
    """Perform one-time actions to prepare the CherryPy core."""
    if cherrypy.codecoverage:
        from cherrypy.lib import covercp
        covercp.start()
    
    conf = cherrypy.config.get
    # TODO: config.checkConfigOptions()
    
    # If sessions are stored in files and we
    # use threading, we need a lock on the file
    if (conf('server.threadPool') > 1
        and conf('session.storageType') == 'file'):
        cherrypy._sessionFileLock = threading.RLock()
    
    # set cgi.maxlen which will limit the size of POST request bodies
    cgi.maxlen = conf('server.maxRequestSize')
    
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
    if not host:
        host = 'localhost'
    
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, int(port)))
        s.close()
        raise IOError("Port %s is in use on %s; perhaps the previous "
                      "server did not shut down properly." %
                      (repr(port), repr(host)))
    except socket.error:
        pass

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
