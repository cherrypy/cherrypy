"""Create and manage the CherryPy application server engine."""

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


class Engine(object):
    """The application server engine, connecting HTTP servers to Requests."""
    
    request_class = _cphttptools.Request
    
    def __init__(self):
        self.state = STOPPED
        
        self.seen_threads = {}
        self.interrupt = None
        
        # Startup/shutdown hooks
        self.on_start_server_list = []
        self.on_stop_server_list = []
        self.on_start_thread_list = []
        self.on_stop_thread_list = []
    
    def setup(self):
        # The only reason this method isn't in __init__ is so that
        # "import cherrypy" can create an Engine() without a circular ref.
        conf = cherrypy.config.get
        
        # Output config options to log
        if conf("server.log_config_options", True):
            cherrypy.config.outputConfigMap()
        
        # Hmmm...we *could* check config in _start instead, but I think
        # most people would like CP to fail before autoreload kicks in.
        err = cherrypy.WrongConfigValue
        for name, section in cherrypy.config.configs.iteritems():
            for k, v in section.iteritems():
                if k == "server.environment":
                    if v and v not in cherrypy.config.environments:
                        raise err("'%s' is not a registered environment." % v)
        
        if cherrypy.codecoverage:
            from cherrypy.lib import covercp
            covercp.start()
        
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
    
    def start(self):
        """Start the application server engine."""
        self.state = STARTING
        self.interrupt = None
        
        conf = cherrypy.config.get
        
        # Autoreload. Note that, if we're not starting our own HTTP server,
        # autoreload could do Very Bad Things when it calls sys.exit, but
        # deployers will just have to be educated and responsible for it.
        if conf('autoreload.on', False):
            try:
                freq = conf('autoreload.frequency', 1)
                autoreload.main(self._start, freq=freq)
            except KeyboardInterrupt:
                cherrypy.log("<Ctrl-C> hit: shutting down autoreloader", "ENGINE")
                self.stop()
            except SystemExit:
                cherrypy.log("SystemExit raised: shutting down autoreloader", "ENGINE")
                self.stop()
                # We must raise here: if this is a process spawned by
                # autoreload, then it must return its error code to
                # the parent.
                raise
            return
        
        self._start()
    
    def _start(self):
        for func in self.on_start_server_list:
            func()
        self.state = STARTED
    
    def block(self):
        """Block forever (wait for KeyboardInterrupt or SystemExit)."""
        try:
            while True:
                time.sleep(.1)
                if self.interrupt:
                    raise self.interrupt
        except KeyboardInterrupt:
            cherrypy.log("<Ctrl-C> hit: shutting down app server", "ENGINE")
            self.stop()
        except SystemExit:
            cherrypy.log("SystemExit raised: shutting down app server", "ENGINE")
            self.stop()
        except:
            # Don't bother logging, since we're going to re-raise.
            self.interrupt = sys.exc_info()[1]
            self.stop()
            raise
    
    def stop(self):
        """Stop the application server engine."""
        for thread_ident, i in self.seen_threads.iteritems():
            for func in self.on_stop_thread_list:
                func(i)
        self.seen_threads.clear()
        
        for func in self.on_stop_server_list:
            func()
        
        self.state = STOPPED
        cherrypy.log("CherryPy shut down", "ENGINE")
    
    def restart(self):
        """Restart the application server engine."""
        self.stop()
        self.start()
    
    def wait(self):
        """Block the caller until ready to receive requests (or error)."""
        while not self.ready:
            time.sleep(.1)
            if self.interrupt:
                msg = "The CherryPy application server errored"
                raise cherrypy.NotReady(msg, "ENGINE")
    
    def _is_ready(self):
        return bool(self.state == STARTED)
    ready = property(_is_ready, doc="Return True if the server is ready to"
                                    " receive requests, False otherwise.")
    
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
            
            for func in self.on_start_thread_list:
                func(i)
        
        r = self.request_class(clientAddress[0], clientAddress[1],
                               remoteHost, scheme)
        cherrypy.serving.request = r
        cherrypy.serving.response = _cphttptools.Response()
        return r

