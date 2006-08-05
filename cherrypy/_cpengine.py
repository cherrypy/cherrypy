"""Create and manage the CherryPy application engine."""

import cgi
import os
import signal
import sys
import threading
import time

import cherrypy
from cherrypy import _cprequest

# Use a flag to indicate the state of the application engine.
STOPPED = 0
STARTING = None
STARTED = 1


def fileattr(m):
    if hasattr(m, "__loader__"):
        if hasattr(m.__loader__, "archive"):
            return m.__loader__.archive
    return getattr(m, "__file__", None)


try:
    if hasattr(signal, "SIGHUP"):
        def SIGHUP(signum=None, frame=None):
            cherrypy.engine.reexec()
        signal.signal(signal.SIGHUP, SIGHUP)

    if hasattr(signal, "SIGTERM"):
        def SIGTERM(signum=None, frame=None):
            cherrypy.server.stop()
            cherrypy.engine.stop()
        signal.signal(signal.SIGTERM, SIGTERM)
except ValueError, _signal_exc:
    if _signal_exc.args[0] != "signal only works in main thread":
        raise

class Engine(object):
    """The application engine, which exposes a request interface to (HTTP) servers."""
    
    request_class = _cprequest.Request
    response_class = _cprequest.Response
    
    def __init__(self):
        self.state = STOPPED
        
        # Startup/shutdown hooks
        self.on_start_engine_list = []
        self.on_stop_engine_list = []
        self.on_start_thread_list = []
        self.on_stop_thread_list = []
        self.seen_threads = {}
        
        self.mtimes = {}
        self.reload_files = []
    
    def start(self, blocking=True):
        """Start the application engine."""
        self.state = STARTING
        
        conf = cherrypy.config.get
        
        # Output config options to log
        if conf("log_config", True):
            cherrypy.config.log_config()
        
        for func in self.on_start_engine_list:
            func()
        self.state = STARTED
        if blocking:
            self.block()
    
    def block(self):
        """Block forever (wait for stop(), KeyboardInterrupt or SystemExit)."""
        try:
            autoreload = cherrypy.config.get('autoreload.on', False)
            if autoreload:
                i = 0
                freq = cherrypy.config.get('autoreload.frequency', 1)
            
            while self.state != STOPPED:
                time.sleep(.1)
                
                # Autoreload
                if autoreload:
                    i += .1
                    if i > freq:
                        i = 0
                        self.autoreload()
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
            # Note that we don't stop the HTTP server here.
            self.stop()
            raise
    
    def reexec(self):
        """Re-execute the current process."""
        cherrypy.server.stop()
        self.stop()
        
        args = sys.argv[:]
        cherrypy.log("Re-spawning %s" % " ".join(args), "ENGINE")
        args.insert(0, sys.executable)
        
        if sys.platform == "win32":
            args = ['"%s"' % arg for arg in args]
        os.execv(sys.executable, args)
    
    def autoreload(self):
        """Reload the process if registered files have been modified."""
        for filename in map(fileattr, sys.modules.values()) + self.reload_files:
            if filename:
                if filename.endswith(".pyc"):
                    filename = filename[:-1]
                
                try:
                    mtime = os.stat(filename).st_mtime
                except OSError:
                    if filename in self.mtimes:
                        # The file was probably deleted.
                        self.reexec()
                
                if filename not in self.mtimes:
                    self.mtimes[filename] = mtime
                    continue
                
                if mtime > self.mtimes[filename]:
                    # The file has been modified.
                    self.reexec()
    
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
    
    def close(self):
        pass
    
    def run(self, request_line, headers, rfile):
        self.method = "GET"
        cherrypy.HTTPError(503, self.msg).set_response()
        cherrypy.response.finalize()
        return cherrypy.response

