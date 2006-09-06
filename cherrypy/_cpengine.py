"""Create and manage the CherryPy application engine."""

import cgi
import os
import re
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
    """Application interface for (HTTP) servers, plus process controls."""
    
    # Configurable attributes
    request_class = _cprequest.Request
    response_class = _cprequest.Response
    deadlock_poll_freq = 60
    autoreload_on = True
    autoreload_frequency = 1
    autoreload_match = ".*"
    
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
        
        for func in self.on_start_engine_list:
            func()
        
        self.state = STARTED
        
        freq = self.deadlock_poll_freq
        if freq > 0:
            self.monitor_thread = threading.Timer(freq, self.monitor)
            self.monitor_thread.start()
        
        if blocking:
            self.block()
    
    def block(self):
        """Block forever (wait for stop(), KeyboardInterrupt or SystemExit)."""
        try:
            while self.state != STOPPED:
                # Note that autoreload_frequency controls
                # sleep timer even if autoreload is off.
                time.sleep(self.autoreload_frequency)
                if self.autoreload_on:
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
        sysfiles = []
        for k, m in sys.modules.items():
            if re.match(self.autoreload_match, k):
                if hasattr(m, "__loader__"):
                    if hasattr(m.__loader__, "archive"):
                        k = m.__loader__.archive
                k = getattr(m, "__file__", None)
                sysfiles.append(k)
        
        for filename in sysfiles + self.reload_files:
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
        """Restart the application engine (does not block)."""
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
    
    def request(self, local_host, remote_host, scheme="http",
                server_protocol="HTTP/1.1"):
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
            req = self.request_class(local_host, remote_host, scheme,
                                     server_protocol)
        cherrypy._serving.request = req
        cherrypy._serving.response = resp = self.response_class()
        self.servings.append((req, resp))
        return req
    
    def monitor(self):
        """Check timeout on all responses (starts a recurring Timer)."""
        if self.state == STARTED:
            for req, resp in self.servings:
                resp.check_timeout()
        freq = self.deadlock_poll_freq
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
    
    # Special thanks to Gavin Baker: http://antonym.org/node/100.
    try:
        import pwd, grp
    except ImportError:
        try:
            os.umask
        except AttributeError:
            def drop_privileges(self):
                """Drop privileges. Not available."""
                raise NotImplementedError
        else:
            # A very conservative umask
            umask = 077
            
            def drop_privileges(self):
                """Drop privileges. Windows version (umask only)."""
                if self.umask is not None:
                    old_umask = os.umask(self.umask)
                    cherrypy.log('umask old: %03o, new: %03o' %
                                 (old_umask, self.umask), "PRIV")
    else:
        uid = None
        gid = None
        # A very conservative umask
        umask = 077
        
        def drop_privileges(self):
            """Drop privileges. UNIX version (uid, gid, and umask)."""
            if not (self.uid is None and self.gid is None):
                def names():
                    name = pwd.getpwuid(os.getuid())[0]
                    group = grp.getgrgid(os.getgid())[0]
                    return name, group
                
                cherrypy.log('Started as %r/%r' % names(), "PRIV")
                if self.gid is not None:
                    os.setgid(grp.getgrnam(self.gid)[2])
                if self.uid is not None:
                    os.setuid(pwd.getpwnam(self.uid)[2])
                cherrypy.log('Running as %r/%r' % names(), "PRIV")
            
            if self.umask is not None:
                old_umask = os.umask(self.umask)
                cherrypy.log('umask old: %03o, new: %03o' %
                             (old_umask, self.umask), "PRIV")


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

