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


class PerpetualTimer(threading._Timer):
    
    def run(self):
        while True:
            self.finished.wait(self.interval)
            if self.finished.isSet():
                return
            self.function(*self.args, **self.kwargs)


class Engine(object):
    """Interface for (HTTP) applications, plus process controls.
    
    Servers and gateways should not instantiate Request objects directly.
    Instead, they should ask an Engine object for a request via the
    Engine.request method.
    
    Blocking is completely optional! The Engine's blocking, signal and
    interrupt handling, privilege dropping, and autoreload features are
    not a good idea when driving CherryPy applications from another
    deployment tool (but an Engine is a great deployment tool itself).
    By calling start(blocking=False), you avoid blocking and interrupt-
    handling issues. By setting Engine.SIGHUP and Engine.SIGTERM to None,
    you can completely disable the signal handling (and therefore disable
    autoreloads triggered by SIGHUP). Set Engine.autoreload_on to False
    to disable autoreload entirely.
    """
    
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
        
        cherrypy.checker()
        
        for func in self.on_start_engine_list:
            func()
        
        self.state = STARTED
        
        self._set_signals()
        
        freq = self.deadlock_poll_freq
        if freq > 0:
            self.monitor_thread = PerpetualTimer(freq, self.monitor)
            self.monitor_thread.setName("CPEngine Monitor")
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
        
        # Some platforms (OS X) will error if all threads are not
        # ABSOLUTELY terminated. See http://www.cherrypy.org/ticket/581.
        for trial in xrange(self.reexec_retry * 10):
            try:
                os.execv(sys.executable, args)
                return
            except OSError, x:
                if x.errno != 45:
                    raise
                time.sleep(0.1)
        else:
            raise
    
    # Number of seconds to retry reexec if os.execv fails.
    reexec_retry = 2
    
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
                self.monitor_thread.join()
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
        """Check timeout on all responses."""
        if self.state == STARTED:
            for req, resp in self.servings:
                resp.check_timeout()
    
    def start_with_callback(self, func, args=None, kwargs=None):
        """Start the given func in a new thread, then start self and block."""
        
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
    
    
    #                           Signal handling                           #
    
    SIGHUP = None
    SIGTERM = None
    
    if hasattr(signal, "SIGHUP"):
        def SIGHUP(self, signum=None, frame=None):
            self.reexec()
    
    if hasattr(signal, "SIGTERM"):
        def SIGTERM(signum=None, frame=None):
            cherrypy.server.stop()
            self.stop()
    
    def _set_signals(self):
        if self.SIGHUP:
            signal.signal(signal.SIGHUP, self.SIGHUP)
        if self.SIGTERM:
            signal.signal(signal.SIGTERM, self.SIGTERM)
    
    
    #                           Drop privileges                           #
    
    # Special thanks to Gavin Baker: http://antonym.org/node/100.
    try:
        import pwd, grp
    except ImportError:
        try:
            os.umask
        except AttributeError:
            def drop_privileges(self):
                """Drop privileges. Not implemented on this platform."""
                raise NotImplementedError
        else:
            umask = None
            
            def drop_privileges(self):
                """Drop privileges. Windows version (umask only)."""
                if self.umask is not None:
                    old_umask = os.umask(self.umask)
                    cherrypy.log('umask old: %03o, new: %03o' %
                                 (old_umask, self.umask), "PRIV")
    else:
        uid = None
        gid = None
        umask = None
        
        def drop_privileges(self):
            """Drop privileges. UNIX version (uid, gid, and umask)."""
            if not (self.uid is None and self.gid is None):
                if self.uid is None:
                    uid = None
                elif isinstance(self.uid, basestring):
                    uid = self.pwd.getpwnam(self.uid)[2]
                else:
                    uid = self.uid
                
                if self.gid is None:
                    gid = None
                elif isinstance(self.gid, basestring):
                    gid = self.grp.getgrnam(self.gid)[2]
                else:
                    gid = self.gid
                
                def names():
                    name = self.pwd.getpwuid(os.getuid())[0]
                    group = self.grp.getgrgid(os.getgid())[0]
                    return name, group
                
                cherrypy.log('Started as %r/%r' % names(), "PRIV")
                if gid is not None:
                    os.setgid(gid)
                if uid is not None:
                    os.setuid(uid)
                cherrypy.log('Running as %r/%r' % names(), "PRIV")
            
            if self.umask is not None:
                old_umask = os.umask(self.umask)
                cherrypy.log('umask old: %03o, new: %03o' %
                             (old_umask, self.umask), "PRIV")


class NotReadyRequest:
    
    throw_errors = True
    show_tracebacks = True
    error_page = {}
    
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

