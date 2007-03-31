"""Plugins for a restsrv Engine."""

import os
import re
try:
    set
except NameError:
    from sets import Set as set
import signal as _signal
import sys
import time
import threading


class SubscribedObject(object):
    """An object whose attributes are manipulable via publishing.
    
    An instance of this class will subscribe to a channel. Messages
    published to that channel should be one of three types:
    
    getattr:
        >>> values = engine.publish('thing', 'attr')
        Note that the 'publish' method will return a list of values
        (from potentially multiple subscribed objects).
    
    setattr:
        >>> engine.publish('thing', 'attr', value)
    
    call:
        >>> engine.publish('thing', 'attr()', *a, **kw)
    """
    
    def __init__(self, engine, channel):
        self.engine = engine
        self.channel = channel
        engine.subscribe(self.channel, self.handle)
    
    def handle(self, attr, *args, **kwargs):
        if attr.endswith("()"):
            # Call
            return getattr(self, attr[:-2])(*args, **kwargs)
        else:
            if args:
                # Set
                return setattr(self, attr, args[0])
            else:
                # Get
                return getattr(self, attr)


class SignalHandler(object):
    
    def __init__(self, engine):
        # Make a map from signal numbers to names
        self.signals = {}
        for k, v in vars(_signal):
            if k.startswith('SIG') and not k.startswith('SIG_'):
                self.signals[v] = k
        
        self.engine = engine
    
    def set_handler(self, signal, callback=None):
        """Register a handler for the given signal (number or name).
        
        If the optional callback is included, it will be registered
        as a listener for the given signal.
        """
        if isinstance(signal, basestring):
            signum = getattr(_signal, signal, None)
            if signum is None:
                return  # ?
            signame = signal
        else:
            signum = signal
            signame = self.signals[signal]
        
        # Should we do something with existing signal handlers?
        # cur = _signal.getsignal(signum)
        _signal.signal(signum, self._handle_signal)
        if callback is not None:
            self.engine.subscribe(signame, callback)
    
    def _handle_signal(self, signum=None, frame=None):
        """Python signal handler (self.set_handler registers it for you)."""
        self.engine.publish(self.signals[signum])


class Reexec(SubscribedObject):
    
    def __init__(self, engine, retry=2):
        self.engine = engine
        self.retry = retry
        engine.subscribe('reexec', self)
    
    def __call__(self):
        """Re-execute the current process."""
        args = sys.argv[:]
        self.engine.log('Re-spawning %s' % ' '.join(args))
        args.insert(0, sys.executable)
        
        if sys.platform == 'win32':
            args = ['"%s"' % arg for arg in args]
        
        # Some platforms (OS X) will error if all threads are not
        # ABSOLUTELY terminated, and there doesn't seem to be a way
        # around it other than waiting for the threads to stop.
        # See http://www.cherrypy.org/ticket/581.
        for trial in xrange(self.retry * 10):
            try:
                os.execv(sys.executable, args)
                return
            except OSError, x:
                if x.errno != 45:
                    raise
                time.sleep(0.1)
        else:
            raise


class DropPrivileges(SubscribedObject):
    """Drop privileges.
    
    Special thanks to Gavin Baker: http://antonym.org/node/100.
    """
    
    def __init__(self, engine):
        self.engine = engine
    
    try:
        import pwd, grp
    except ImportError:
        try:
            os.umask
        except AttributeError:
            def __call__(self):
                """Drop privileges. Not implemented on this platform."""
                raise NotImplementedError
        else:
            umask = None
            
            def __call__(self):
                """Drop privileges. Windows version (umask only)."""
                if umask is not None:
                    old_umask = os.umask(umask)
                    self.engine.log('umask old: %03o, new: %03o' %
                                    (old_umask, umask))
    else:
        uid = None
        gid = None
        umask = None
        
        def __call__(self):
            """Drop privileges. UNIX version (uid, gid, and umask)."""
            if not (uid is None and gid is None):
                if uid is None:
                    uid = None
                elif isinstance(uid, basestring):
                    uid = pwd.getpwnam(uid)[2]
                else:
                    uid = uid
                
                if gid is None:
                    gid = None
                elif isinstance(gid, basestring):
                    gid = grp.getgrnam(gid)[2]
                else:
                    gid = gid
                
                def names():
                    name = pwd.getpwuid(os.getuid())[0]
                    group = grp.getgrgid(os.getgid())[0]
                    return name, group
                
                self.engine.log('Started as %r/%r' % names())
                if gid is not None:
                    os.setgid(gid)
                if uid is not None:
                    os.setuid(uid)
                self.engine.log('Running as %r/%r' % names())
            
            if umask is not None:
                old_umask = os.umask(umask)
                self.engine.log('umask old: %03o, new: %03o' %
                                (old_umask, umask))
    __call__.priority = 70


def daemonize(stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
    """Daemonize the running script.
    
    When this method returns, the process is completely decoupled from the
    parent environment."""
    
    # See http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
    # and http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/66012
    
    # Finish up with the current stdout/stderr
    sys.stdout.flush()
    sys.stderr.flush()
    
    # Do first fork.
    try:
        pid = os.fork()
        if pid == 0:
            # This is the child process. Continue.
            pass
        else:
            # This is the first parent. Exit, now that we've forked.
            sys.stdout.close()
            sys.exit(0)
    except OSError, exc:
        # Python raises OSError rather than returning negative numbers.
        sys.exit("%s: fork #1 failed: (%d) %s\n" % (sys.argv[0], exc.errno, exc.strerror))
    
    os.setsid()
    
    # Do second fork
    try:
        pid = os.fork()
        if pid > 0:
            sys.stdout.close()
            sys.exit(0) # Exit second parent
    except OSError, exc:
        sys.exit("%s: fork #2 failed: (%d) %s\n" % (sys.argv[0], exc.errno, exc.strerror))
    
    os.chdir("/")
    os.umask(0)
    
    si = open(stdin, "r")
    so = open(stdout, "a+")
    se = open(stderr, "a+", 0)
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())
daemonize.priority = 10


class PIDFile(object):
    
    def __init__(self, engine, pidfile):
        self.engine = engine
        self.pidfile = pidfile
        engine.subscribe('start', self.start)
        engine.subscribe('stop', self.stop)
    
    def start(self):
        open(self.pidfile, "wb").write(str(os.getpid()))
    start.priority = 70
    
    def stop(self):
        try:
            os.remove(self.pidfile)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            pass


class PerpetualTimer(threading._Timer):
    
    def run(self):
        while True:
            self.finished.wait(self.interval)
            if self.finished.isSet():
                return
            self.function(*self.args, **self.kwargs)


class Monitor(SubscribedObject):
    """Subscriber which periodically runs a callback in a separate thread."""
    
    frequency = 60
    
    def __init__(self, engine, callback, channel=None):
        self.callback = callback
        self.thread = None
        
        if channel is None:
            channel = self.__class__.__name__
        SubscribedObject.__init__(self, engine, channel)
        
        self.listeners = [('start', self.start),
                          ('stop', self.stop),
                          ('graceful', self.graceful),
                          ]
        self.attach()
    
    def attach(self):
        for point, callback in self.listeners:
            self.engine.subscribe(point, callback)
    
    def detach(self):
        for point, callback in self.listeners:
            self.engine.unsubscribe(point, callback)
    
    def start(self):
        if self.frequency > 0:
            self.thread = PerpetualTimer(self.frequency, self.callback)
            self.thread.setName("restsrv %s" % self.channel)
            self.thread.start()
    
    def stop(self):
        if self.thread:
            if self.thread is not threading.currentThread():
                self.thread.cancel()
                self.thread.join()
            self.thread = None
    
    def graceful(self):
        self.stop()
        self.start()


class Autoreloader(Monitor):
    """Monitor which re-executes the process when files change."""
    
    frequency = 1
    match = '.*'
    
    def __init__(self, engine):
        self.mtimes = {}
        self.files = set()
        Monitor.__init__(self, engine, self.run)
    
    def add(self, filename):
        self.files.add(filename)
    
    def discard(self, filename):
        self.files.discard(filename)
    
    def start(self):
        self.mtimes = {}
        self.files = set()
        Monitor.start(self)
    
    def run(self):
        """Reload the process if registered files have been modified."""
        sysfiles = set()
        for k, m in sys.modules.items():
            if re.match(self.match, k):
                if hasattr(m, '__loader__'):
                    if hasattr(m.__loader__, 'archive'):
                        k = m.__loader__.archive
                k = getattr(m, '__file__', None)
                sysfiles.add(k)
        
        for filename in sysfiles | self.files:
            if filename:
                if filename.endswith('.pyc'):
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
                        self.engine.publish('reexec')


class ThreadManager(object):
    """Manager for HTTP request threads.
    
    If you have control over thread creation and destruction, publish to
    the 'acquire_thread' and 'release_thread' channels (for each thread).
    This will register/unregister the current thread and publish to
    'start_thread' and 'stop_thread' listeners in the engine as needed.
    
    If threads are created and destroyed by code you do not control (e.g.,
    Apache), then, at the beginning of every HTTP request, publish to
    'acquire_thread' only. You should not publish to 'release_thread' in
    this case, since you do not know whether the thread will be re-used or
    not. The engine will call 'stop_thread' listeners for you when it stops.
    """
    
    def __init__(self, engine):
        self.threads = {}
        self.engine = engine
        engine.subscribe('acquire_thread', self.acquire)
        engine.subscribe('release_thread', self.release)
        engine.subscribe('stop', self.release_all)
        engine.subscribe('graceful', self.release_all)
    
    def acquire(self):
        """Run 'start_thread' listeners for the current thread. Idempotent."""
        thread_ident = threading._get_ident()
        if thread_ident not in self.threads:
            # We can't just use _get_ident as the thread ID
            # because some platforms reuse thread ID's.
            i = len(self.threads) + 1
            self.threads[thread_ident] = i
            self.engine.publish('start_thread', i)
    
    def release(self):
        """Release the current thread and run 'stop_thread' listeners."""
        thread_ident = threading._get_ident()
        i = self.threads.pop(thread_ident, None)
        if i is not None:
            self.engine.publish('stop_thread', i)
    
    def release_all(self):
        for thread_ident, i in self.threads.iteritems():
            self.engine.publish('stop_thread', i)
        self.threads.clear()
