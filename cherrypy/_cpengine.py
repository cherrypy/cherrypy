"""Create and manage the CherryPy application engine."""

import cgi
import sys
import threading
import time

import cherrypy
from cherrypy import _cprequest
from cherrypy.lib import autoreload

# Use a flag to indicate the state of the application engine.
STOPPED = 0
STARTING = None
STARTED = 1


class Engine(object):
    """The application engine, which exposes a request interface to (HTTP) servers."""
    
    request_class = _cprequest.Request
    response_class = _cprequest.Response
    
    def __init__(self):
        self.state = STOPPED
        self.interrupt = None
        
        # Startup/shutdown hooks
        self.on_start_engine_list = []
        self.on_stop_engine_list = []
        self.on_start_thread_list = []
        self.on_stop_thread_list = []
        self.seen_threads = {}
    
    def start(self, blocking=True):
        """Start the application engine."""
        self.state = STARTING
        self.interrupt = None
        
        conf = cherrypy.config.get
        
        # Output config options to log
        if conf("log_config_options", True):
            cherrypy.config.output_config_map()
        
        if cherrypy.codecoverage:
            from cherrypy.lib import covercp
            covercp.start()
        
        # Autoreload. Note that, if we're not starting our own HTTP server,
        # autoreload could do Very Bad Things when it calls sys.exit, but
        # deployers will just have to be educated and responsible for it.
        if conf('autoreload.on', False):
            try:
                freq = conf('autoreload.frequency', 1)
                autoreload.main(self._start, args=(blocking,), freq=freq)
            except KeyboardInterrupt:
                cherrypy.log("<Ctrl-C> hit: shutting down autoreloader", "ENGINE")
                cherrypy.server.stop()
                self.stop()
            except SystemExit:
                cherrypy.log("SystemExit raised: shutting down autoreloader", "ENGINE")
                cherrypy.server.stop()
                self.stop()
                # We must raise here: if this is a process spawned by
                # autoreload, then it must return its error code to
                # the parent.
                raise
            return
        
        self._start(blocking)
    
    def _start(self, blocking=True):
        # This is in a separate function so autoreload can call it.
        for func in self.on_start_engine_list:
            func()
        self.state = STARTED
        if blocking:
            self.block()
    
    def block(self):
        """Block forever (wait for stop(), KeyboardInterrupt or SystemExit)."""
        try:
            while self.state != STOPPED:
                time.sleep(.1)
                if self.interrupt:
                    raise self.interrupt
        except KeyboardInterrupt:
            cherrypy.log("<Ctrl-C> hit: shutting down app engine", "ENGINE")
            cherrypy.server.stop()
            self.stop()
        except SystemExit:
            cherrypy.log("SystemExit raised: shutting down app engine", "ENGINE")
            cherrypy.server.stop()
            self.stop()
            raise
        except:
            # Don't bother logging, since we're going to re-raise.
            self.interrupt = sys.exc_info()[1]
            # Note that we don't stop the HTTP server here.
            self.stop()
            raise
    
    def stop(self):
        """Stop the application engine."""
        if self.state != STOPPED:
            for thread_ident, i in self.seen_threads.iteritems():
                for func in self.on_stop_thread_list:
                    func(i)
            self.seen_threads.clear()
            
            for func in self.on_stop_engine_list:
                func()
            
            self.state = STOPPED
            cherrypy.log("CherryPy shut down", "ENGINE")
    
    def restart(self):
        """Restart the application engine (doesn't block)."""
        self.stop()
        self.start(blocking=False)
    
    def wait(self):
        """Block the caller until ready to receive requests (or error)."""
        while not self.ready:
            time.sleep(.1)
            if self.interrupt:
                raise self.interrupt
    
    def _is_ready(self):
        return bool(self.state == STARTED)
    ready = property(_is_ready, doc="Return True if the engine is ready to"
                                    " receive requests, False otherwise.")
    
    def request(self, client_address, remote_host, scheme="http"):
        """Obtain an HTTP Request object.
        
        client_address: the (IP address, port) of the client
        remote_host should be the client's host name. If not available
            (because no reverse DNS lookup is performed), the client
            IP should be provided.
        scheme: either "http" or "https"; defaults to "http"
        """
        if self.state == STOPPED:
            r = NotReadyRequest("The CherryPy engine has stopped.")
        elif self.state == STARTING:
            r = NotReadyRequest("The CherryPy engine could not start.")
        else:
            # Only run on_start_thread_list if the engine is running.
            threadID = threading._get_ident()
            if threadID not in self.seen_threads:
                
                if cherrypy.codecoverage:
                    from cherrypy.lib import covercp
                    covercp.start()
                
                i = len(self.seen_threads) + 1
                self.seen_threads[threadID] = i
                
                for func in self.on_start_thread_list:
                    func(i)
            r = self.request_class(client_address[0], client_address[1],
                                   remote_host, scheme)
        cherrypy.serving.request = r
        cherrypy.serving.response = self.response_class()
        return r
    
    def start_with_callback(self, func, args=None, kwargs=None):
        """Start, then callback the given func in a new thread."""
        
        if args is None:
            args = ()
        if kwargs is None:
            kwargs = {}
        args = (func,) + args
        
        def _callback(func, *a, **kw):
            self.wait()
            func(*a, **kw)
        t = threading.Thread(target=_callback, args=args, kwargs=kwargs)
        t.setName("CPEngine Callback " + t.getName())
        t.start()
        
        self.start()


class NotReadyRequest:
    
    def __init__(self, msg):
        self.msg = msg
    
    def run(self, request_line, headers, rfile):
        self.method = "GET"
        cherrypy.HTTPError(503, self.msg).set_response()
        cherrypy.response.finalize()
        return cherrypy.response

