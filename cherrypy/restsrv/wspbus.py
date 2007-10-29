"""An implementation of the Web Site Process Bus.

This module is completely standalone, depending only on the stdlib.

Web Site Process Bus
--------------------

A Bus object is used to contain and manage site-wide behavior:
daemonization, HTTP server start/stop, process reload, signal handling,
drop privileges, PID file management, logging for all of these,
and many more.

In addition, a Bus object provides a place for each web framework
to register code that runs in response to site-wide events (like
process start and stop), or which controls or otherwise interacts with
the site-wide components mentioned above. For example, a framework which
uses file-based templates would add known template filenames to an
autoreload component.

Ideally, a Bus object will be flexible enough to be useful in a variety
of invocation scenarios:

 1. The deployer starts a site from the command line via a framework-
     neutral deployment script; applications from multiple frameworks
     are mixed in a single site. Command-line arguments and configuration
     files are used to define site-wide components such as the HTTP server,
     WSGI component graph, autoreload behavior, signal handling, etc.
 2. The deployer starts a site via some other process, such as Apache;
     applications from multiple frameworks are mixed in a single site.
     Autoreload and signal handling (from Python at least) are disabled.
 3. The deployer starts a site via a framework-specific mechanism;
     for example, when running tests, exploring tutorials, or deploying
     single applications from a single framework. The framework controls
     which site-wide components are enabled as it sees fit.

The Bus object in this package uses topic-based publish-subscribe
messaging to accomplish all this. A few topic channels are built in
('start', 'stop', 'exit', and 'graceful'). Frameworks and site containers
are free to define their own. If a message is sent to a channel that has
not been defined or has no listeners, there is no effect.

In general, there should only ever be a single Bus object per process.
Frameworks and site containers share a single Bus object by publishing
messages and subscribing listeners.

The Bus object works as a finite state machine which models the current
state of the process. Bus methods move it from one state to another;
those methods then publish to subscribed listeners on the channel for
the new state.

                        O
                        |
                        V
       STOPPING --> STOPPED --> X
          A   A         |
          |    \___     |
          |        \    |
          |         V   V
        STARTED <-- STARTING

"""

import os
try:
    set
except NameError:
    from sets import Set as set
import sys
import threading
import time
import traceback as _traceback


# Use a flag to indicate the state of the bus.
class _StateEnum(object):
    class State(object):
        pass
states = _StateEnum()
states.STOPPED = states.State()
states.STARTING = states.State()
states.STARTED = states.State()
states.STOPPING = states.State()


class Bus(object):
    """Process state-machine and messenger for HTTP site deployment.
    
    All listeners for a given channel are guaranteed to be called even
    if others at the same channel fail. Each failure is logged, but
    execution proceeds on to the next listener. The only way to stop all
    processing from inside a listener is to raise SystemExit and stop the
    whole server.
    """
    
    states = states
    state = states.STOPPED
    execv = False
    
    def __init__(self):
        self.execv = False
        self.state = states.STOPPED
        self.listeners = dict(
            [(channel, set()) for channel
             in ('start', 'stop', 'exit', 'graceful')])
        self._priorities = {}
    
    def subscribe(self, channel, callback, priority=None):
        """Add the given callback at the given channel (if not present)."""
        if channel not in self.listeners:
            self.listeners[channel] = set()
        self.listeners[channel].add(callback)
        
        if priority is None:
            priority = getattr(callback, 'priority', 50)
        self._priorities[(channel, callback)] = priority
    
    def unsubscribe(self, channel, callback):
        """Discard the given callback (if present)."""
        listeners = self.listeners.get(channel)
        if listeners and callback in listeners:
            listeners.discard(callback)
            del self._priorities[(channel, callback)]
    
    def publish(self, channel, *args, **kwargs):
        """Return output of all subscribers for the given channel."""
        if channel not in self.listeners:
            return []
        
        exc = None
        output = []
        
        items = [(self._priorities[(channel, listener)], listener)
                 for listener in self.listeners[channel]]
        items.sort()
        for priority, listener in items:
            try:
                output.append(listener(*args, **kwargs))
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                self.log("Error in %r listener %r" % (channel, listener),
                         traceback=True)
                exc = sys.exc_info()[1]
        if exc:
            raise
        return output
    
    def start(self):
        """Start all services."""
        self.state = states.STARTING
        self.log('Bus starting')
        try:
            self.publish('start')
        except:
            try:
                self.stop()
            except:
                # Any stop errors will be logged inside publish().
                pass
            raise
        self.state = states.STARTED
    
    def exit(self, status=0):
        """Stop all services and exit the process."""
        self.stop()
        self.log('Bus exit')
        self.publish('exit')
        sys.exit(status)
    
    def restart(self):
        """Restart the process (may close connections).
        
        This method does not restart the process from the calling thread;
        instead, it stops the bus and asks the main thread to call execv.
        """
        self.execv = True
        self.stop()
    
    def graceful(self):
        """Advise all services to reload."""
        self.log('Bus graceful')
        self.publish('graceful')
    
    def block(self, state=states.STOPPED, interval=0.1):
        """Wait for the given state, KeyboardInterrupt or SystemExit."""
        try:
            while self.state != state:
                time.sleep(interval)
            if self.execv:
                self._do_execv()
        except (KeyboardInterrupt, IOError):
            # The time.sleep call might raise
            # "IOError: [Errno 4] Interrupted function call" on KBInt.
            self.log('Keyboard Interrupt: shutting down bus')
            self.stop()
        except SystemExit:
            self.log('SystemExit raised: shutting down bus')
            self.stop()
            raise
    
    def _do_execv(self):
        """Re-execute the current process."""
        self.execv = False
        
        self.log('Bus restart')
        self.publish('exit')
        
        # Re-execute the current process. We must do this in the
        # main thread (which is the only thread that should be
        # calling block) because OS X doesn't allow execv to be
        # called in a child thread very well.
        # Waiting for ALL child threads to finish is necessary on OS X.
        # See: http://www.cherrypy.org/ticket/581
        self.log("Waiting for child threads to terminate...")
        for t in threading.enumerate():
            if t != threading.currentThread():
                t.join()
        
        args = sys.argv[:]
        self.log('Re-spawning %s' % ' '.join(args))
        args.insert(0, sys.executable)
        
        if sys.platform == 'win32':
            args = ['"%s"' % arg for arg in args]
        
        os.execv(sys.executable, args)
    
    def stop(self):
        """Stop all services."""
        self.state = states.STOPPING
        self.log('Bus stopping')
        self.publish('stop')
        self.state = states.STOPPED
    
    def start_with_callback(self, func, args=None, kwargs=None):
        """Start 'func' in a new thread T, then start self (and return T)."""
        if args is None:
            args = ()
        if kwargs is None:
            kwargs = {}
        args = (func,) + args
        
        def _callback(func, *a, **kw):
            self.block(states.STARTED)
            func(*a, **kw)
        t = threading.Thread(target=_callback, args=args, kwargs=kwargs)
        t.setName('Bus Callback ' + t.getName())
        t.start()
        
        self.start()
        
        return t
    
    def log(self, msg="", traceback=False):
        """Log the given message. Append the last traceback if requested."""
        if traceback:
            exc = sys.exc_info()
            msg += "\n" + "".join(_traceback.format_exception(*exc))
        self.publish('log', msg)

bus = Bus()
