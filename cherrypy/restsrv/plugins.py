"""Site services for use with a Web Site Process Bus."""

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


class SimplePlugin(object):
    """Plugin base class which auto-subscribes methods for known channels."""
    
    def subscribe(self):
        """Register this object as a (multi-channel) listener on the bus."""
        for channel in self.bus.listeners:
            method = getattr(self, channel, None)
            if method is not None:
                self.bus.subscribe(channel, method)
    
    def unsubscribe(self):
        """Unregister this object as a listener on the bus."""
        for channel in self.bus.listeners:
            method = getattr(self, channel, None)
            if method is not None:
                self.bus.unsubscribe(channel, method)



class SignalHandler(object):
    """Register bus channels (and listeners) for system signals.
    
    By default, instantiating this object subscribes the following signals
    and listeners:
    
        TERM: bus.exit
        HUP : bus.restart
        USR1: bus.graceful
    """
    
    # Map from signal numbers to names
    signals = {}
    for k, v in vars(_signal).items():
        if k.startswith('SIG') and not k.startswith('SIG_'):
            signals[v] = k
    del k, v
    
    def __init__(self, bus):
        self.bus = bus
        # Set default handlers
        self.handlers = {'SIGTERM': self.bus.exit,
                         'SIGHUP': self.bus.restart,
                         'SIGUSR1': self.bus.graceful,
                         }
    
    def subscribe(self):
        for sig, func in self.handlers.iteritems():
            try:
                self.set_handler(sig, func)
            except ValueError:
                pass
    
    def set_handler(self, signal, listener=None):
        """Subscribe a handler for the given signal (number or name).
        
        If the optional 'listener' argument is provided, it will be
        subscribed as a listener for the given signal's channel.
        
        If the given signal name or number is not available on the current
        platform, ValueError is raised.
        """
        if isinstance(signal, basestring):
            signum = getattr(_signal, signal, None)
            if signum is None:
                raise ValueError("No such signal: %r" % signal)
            signame = signal
        else:
            try:
                signame = self.signals[signal]
            except KeyError:
                raise ValueError("No such signal: %r" % signal)
            signum = signal
        
        # Should we do something with existing signal handlers?
        # cur = _signal.getsignal(signum)
        _signal.signal(signum, self._handle_signal)
        if listener is not None:
            self.bus.log("Listening for %s." % signame)
            self.bus.subscribe(signame, listener)
    
    def _handle_signal(self, signum=None, frame=None):
        """Python signal handler (self.set_handler subscribes it for you)."""
        signame = self.signals[signum]
        self.bus.log("Caught signal %s." % signame)
        self.bus.publish(signame)


class DropPrivileges(SimplePlugin):
    """Drop privileges.
    
    Special thanks to Gavin Baker: http://antonym.org/node/100.
    """
    
    def __init__(self, bus):
        self.bus = bus
        self.finalized = False
    
    try:
        import pwd, grp
    except ImportError:
        try:
            os.umask
        except AttributeError:
            def start(self):
                """Drop privileges. Not implemented on this platform."""
                raise NotImplementedError
        else:
            umask = None
            
            def start(self):
                """Drop privileges. Windows version (umask only)."""
                if self.finalized:
                    self.bus.log('umask already set to: %03o' % umask)
                else:
                    if umask is None:
                        self.bus.log('umask not set')
                    else:
                        old_umask = os.umask(umask)
                        self.bus.log('umask old: %03o, new: %03o' %
                                     (old_umask, umask))
                    self.finalized = True
    else:
        uid = None
        gid = None
        umask = None
        
        def start(self):
            """Drop privileges. UNIX version (uid, gid, and umask)."""
            if uid is None and gid is None:
                self.bus.log('uid/gid not set')
            else:
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
                
                if self.finalized:
                    self.bus.log('Already running as: %r/%r' % names())
                else:
                    self.bus.log('Started as %r/%r' % names())
                    if gid is not None:
                        os.setgid(gid)
                    if uid is not None:
                        os.setuid(uid)
                    self.bus.log('Running as %r/%r' % names())
            
            if self.finalized:
                self.bus.log('umask already set to: %03o' % umask)
            else:
                if umask is None:
                    self.bus.log('umask not set')
                else:
                    old_umask = os.umask(umask)
                    self.bus.log('umask old: %03o, new: %03o' %
                                 (old_umask, umask))
                self.finalized = True
    start.priority = 75


class Daemonizer(SimplePlugin):
    """Daemonize the running script.
    
    Use this with a Web Site Process Bus via:
        
        Daemonizer(bus).subscribe()
    
    When this component finishes, the process is completely decoupled from
    the parent environment.
    """
    
    def __init__(self, bus, stdin='/dev/null', stdout='/dev/null',
                 stderr='/dev/null'):
        self.bus = bus
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.finalized = False
    
    def start(self):
        if self.finalized:
            self.bus.log('Already deamonized.')
        
        # forking has issues with threads:
        # http://www.opengroup.org/onlinepubs/000095399/functions/fork.html
        # "The general problem with making fork() work in a multi-threaded
        #  world is what to do with all of the threads..."
        # So we check for active threads:
        if threading.activeCount() != 1:
            self.bus.log('There are %r active threads. '
                         'Daemonizing now may cause strange failures.' %
                         threading.enumerate())
        
        # See http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
        # (or http://www.faqs.org/faqs/unix-faq/programmer/faq/ section 1.7)
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
                self.bus.log('Forking once.')
                sys.exit(0)
        except OSError, exc:
            # Python raises OSError rather than returning negative numbers.
            sys.exit("%s: fork #1 failed: (%d) %s\n"
                     % (sys.argv[0], exc.errno, exc.strerror))
        
        os.setsid()
        
        # Do second fork
        try:
            pid = os.fork()
            if pid > 0:
                self.bus.log('Forking twice.')
                sys.exit(0) # Exit second parent
        except OSError, exc:
            sys.exit("%s: fork #2 failed: (%d) %s\n"
                     % (sys.argv[0], exc.errno, exc.strerror))
        
        os.chdir("/")
        os.umask(0)
        
        si = open(self.stdin, "r")
        so = open(self.stdout, "a+")
        se = open(self.stderr, "a+", 0)

        # os.dup2(fd,fd2) will close fd2 if necessary (so we don't explicitly close
        # stdin,stdout,stderr):
        # http://docs.python.org/lib/os-fd-ops.html 
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())
        
        self.bus.log('Daemonized to PID: %s' % os.getpid())
        self.finalized = True
    start.priority = 65


class PIDFile(SimplePlugin):
    """Maintain a PID file via a WSPBus."""
    
    def __init__(self, bus, pidfile):
        self.bus = bus
        self.pidfile = pidfile
        self.finalized = False
    
    def start(self):
        pid = os.getpid()
        if self.finalized:
            self.bus.log('PID %r already written to %r.' % (pid, self.pidfile))
        else:
            open(self.pidfile, "wb").write(str(pid))
            self.bus.log('PID %r written to %r.' % (pid, self.pidfile))
            self.finalized = True
    start.priority = 70
    
    def exit(self):
        try:
            os.remove(self.pidfile)
            self.bus.log('PID file removed: %r.' % self.pidfile)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            pass


class PerpetualTimer(threading._Timer):
    """A subclass of threading._Timer whose run() method repeats."""
    
    def run(self):
        while True:
            self.finished.wait(self.interval)
            if self.finished.isSet():
                return
            self.function(*self.args, **self.kwargs)


class Monitor(SimplePlugin):
    """WSPBus listener to periodically run a callback in its own thread.
    
    bus: a Web Site Process Bus object.
    callback: the function to call at intervals.
    frequency: the time in seconds between callback runs.
    """
    
    frequency = 60
    
    def __init__(self, bus, callback, frequency=60):
        self.bus = bus
        self.callback = callback
        self.frequency = frequency
        self.thread = None
    
    def start(self):
        """Start our callback in its own perpetual timer thread."""
        if self.frequency > 0:
            if self.thread is None:
                threadname = "restsrv %s" % self.__class__.__name__
                self.thread = PerpetualTimer(self.frequency, self.callback)
                self.thread.setName(threadname)
                self.thread.start()
                self.bus.log("Started thread %r." % threadname)
            else:
                self.bus.log("Thread %r already started." % threadname)
    start.priority = 70
    
    def stop(self):
        """Stop our callback's perpetual timer thread."""
        if self.thread is None:
            self.bus.log("No thread running for %s." % self.__class__.__name__)
        else:
            if self.thread is not threading.currentThread():
                self.thread.cancel()
                self.thread.join()
                self.bus.log("Stopped thread %r." % self.thread.getName())
            self.thread = None
    
    def graceful(self):
        """Stop the callback's perpetual timer thread and restart it."""
        self.stop()
        self.start()


class Autoreloader(Monitor):
    """Monitor which re-executes the process when files change."""
    
    frequency = 1
    match = '.*'
    
    def __init__(self, bus, frequency=1, match='.*'):
        self.mtimes = {}
        self.files = set()
        self.match = match
        Monitor.__init__(self, bus, self.run, frequency)
    
    def start(self):
        """Start our own perpetual timer thread for self.run."""
        if self.thread is None:
            self.mtimes = {}
        Monitor.start(self)
    start.priority = 70 
    
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
                        self.bus.log("Restarting because %s changed." % filename)
                        self.thread.cancel()
                        self.bus.log("Stopped thread %r." % self.thread.getName())
                        self.bus.restart()
                        return


class ThreadManager(SimplePlugin):
    """Manager for HTTP request threads.
    
    If you have control over thread creation and destruction, publish to
    the 'acquire_thread' and 'release_thread' channels (for each thread).
    This will register/unregister the current thread and publish to
    'start_thread' and 'stop_thread' listeners in the bus as needed.
    
    If threads are created and destroyed by code you do not control
    (e.g., Apache), then, at the beginning of every HTTP request,
    publish to 'acquire_thread' only. You should not publish to
    'release_thread' in this case, since you do not know whether
    the thread will be re-used or not. The bus will call
    'stop_thread' listeners for you when it stops.
    """
    
    def __init__(self, bus):
        self.threads = {}
        self.bus = bus
        self.bus.listeners.setdefault('acquire_thread', set())
        self.bus.listeners.setdefault('release_thread', set())
    
    def acquire_thread(self):
        """Run 'start_thread' listeners for the current thread.
        
        If the current thread has already been seen, any 'start_thread'
        listeners will not be run again.
        """
        thread_ident = threading._get_ident()
        if thread_ident not in self.threads:
            # We can't just use _get_ident as the thread ID
            # because some platforms reuse thread ID's.
            i = len(self.threads) + 1
            self.threads[thread_ident] = i
            self.bus.publish('start_thread', i)
    
    def release_thread(self):
        """Release the current thread and run 'stop_thread' listeners."""
        thread_ident = threading._get_ident()
        i = self.threads.pop(thread_ident, None)
        if i is not None:
            self.bus.publish('stop_thread', i)
    
    def stop(self):
        """Release all threads and run all 'stop_thread' listeners."""
        for thread_ident, i in self.threads.iteritems():
            self.bus.publish('stop_thread', i)
        self.threads.clear()
    graceful = stop

