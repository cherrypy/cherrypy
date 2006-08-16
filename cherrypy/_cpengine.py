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
        
        self.servings = []
        
        self.mtimes = {}
        self.reload_files = []
        
        self.monitor_thread = None
    
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
        
        freq = float(cherrypy.config.get('deadlock_poll_freq', 60))
        if freq > 0:
            self.monitor_thread = threading.Timer(freq, self.monitor)
            self.monitor_thread.start()
        
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
                
                oldtime = self.mtimes.get(filename, 0)
                if oldtime is None:
                    # Module with no .py file. Skip it.
                    continue
                
                try:
                    mtime = os.stat(filename).st_mtime
                except OSError:
                    # Either a module with no .py file, or it's been deleted.
                    mtime = None
                
                if filename not in self.mtimes:
                    # If a module has no .py file, this will be None.
                    self.mtimes[filename] = mtime
                else:
                    if mtime is None or mtime > oldtime:
                        # The file has been deleted or modified.
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
            
            if self.monitor_thread:
                self.monitor_thread.cancel()
                self.monitor_thread = None
            
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
    
    def request(self, local_host, remote_host, scheme="http"):
        """Obtain an HTTP Request object.
        
        local_host should be an http.Host object with the server info.
        remote_host should be an http.Host object with the client info.
        scheme: either "http" or "https"; defaults to "http"
        """
        if self.state == STOPPED:
            req = NotReadyRequest("The CherryPy engine has stopped.")
        elif self.state == STARTING:
            req = NotReadyRequest("The CherryPy engine could not start.")
        else:
            # Only run on_start_thread_list if the engine is running.
            threadID = threading._get_ident()
            if threadID not in self.seen_threads:
                i = len(self.seen_threads) + 1
                self.seen_threads[threadID] = i
                
                for func in self.on_start_thread_list:
                    func(i)
            req = self.request_class(local_host, remote_host, scheme)
        cherrypy.serving.request = req
        cherrypy.serving.response = resp = self.response_class()
        self.servings.append((req, resp))
        return req
    
    def monitor(self):
        """Check timeout on all responses."""
        if self.state == STARTED:
            for req, resp in self.servings:
                resp.check_timeout()
            freq = float(cherrypy.config.get('deadlock_poll_freq', 60))
            self.monitor_thread = threading.Timer(freq, self.monitor)
            self.monitor_thread.start()
    
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
        self.protocol = (1,1)
    
    def close(self):
        pass
    
    def run(self, method, path, query_string, protocol, headers, rfile):
        self.method = "GET"
        cherrypy.HTTPError(503, self.msg).set_response()
        cherrypy.response.finalize()
        return cherrypy.response


def drop_privileges(new_user='nobody', new_group='nogroup'):
    """Drop privileges. UNIX only."""
    # Special thanks to Gavin Baker: http://antonym.org/node/100.
    
    import pwd, grp
    
    def names():
        return pwd.getpwuid(os.getuid())[0], grp.getgrgid(os.getgid())[0]
    name, group = names()
    cherrypy.log('Started as %r/%r' % (name, group), "PRIV")
    
    if os.getuid() != 0:
        # We're not root so, like, whatever dude.
        cherrypy.log("Already running as %r" % name, "PRIV")
        return
    
    # Try setting the new uid/gid (from new_user/new_group).
    try:
        os.setgid(grp.getgrnam(new_group)[2])
    except OSError, e:
        cherrypy.log('Could not set effective group id: %r' % e, "PRIV")
    
    try:
        os.setuid(pwd.getpwnam(new_user)[2])
    except OSError, e:
        cherrypy.log('Could not set effective user id: %r' % e, "PRIV")
    
    # Ensure a very convervative umask
    old_umask = os.umask(077)
    cherrypy.log('Old umask: %o, new umask: 077' % old_umask, "PRIV")
    cherrypy.log('Running as %r/%r' % names(), "PRIV")

