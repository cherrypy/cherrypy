"""Base Engine class for restsrv."""

try:
    set
except NameError:
    from sets import Set as set
import sys
import threading
import time
import traceback


# Use a flag to indicate the state of the engine.
STOPPED = 0
STARTING = None
STARTED = 1


class Engine(object):
    """Process controls for HTTP site deployment."""
    
    state = STOPPED
    
    def __init__(self):
        self.state = STOPPED
        self.listeners = {}
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
            # All listeners for a given channel are guaranteed to run even
            # if others at the same channel fail. We will still log the
            # failure, but proceed on to the next listener. The only way
            # to stop all processing from one of these listeners is to
            # raise SystemExit and stop the whole server.
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
        """Start the engine."""
        self.state = STARTING
        self.log('Engine starting')
        self.publish('start')
        self.state = STARTED
    
    def wait(self, interval=0.1):
        """Block the caller until the Engine is in the STARTED state."""
        while not (self.state == STARTED):
            time.sleep(interval)
    
    def exit(self, status=0):
        """Stop the engine and exit the process."""
        self.stop()
        sys.exit(status)
    
    def restart(self):
        """Restart the process (may close connections)."""
        self.stop()
        self.log('Engine restart')
        self.publish('reexec')
    
    def graceful(self):
        """Restart the engine without closing connections."""
        self.log('Engine graceful restart')
        self.publish('graceful')
    
    def block(self, interval=1):
        """Block forever (wait for stop(), KeyboardInterrupt or SystemExit)."""
        try:
            while self.state != STOPPED:
                time.sleep(interval)
        except (KeyboardInterrupt, IOError):
            # The time.sleep call might raise
            # "IOError: [Errno 4] Interrupted function call".
            self.log('Keyboard Interrupt: shutting down engine')
            self.stop()
        except SystemExit:
            self.log('SystemExit raised: shutting down engine')
            self.stop()
            raise
    
    def stop(self):
        """Stop the engine."""
        if self.state != STOPPED:
            self.log('Engine shutting down')
            self.publish('stop')
            self.state = STOPPED
    
    def start_with_callback(self, func, args=None, kwargs=None):
        """Start 'func' in a new thread T, then start self (and return T)."""
        if args is None:
            args = ()
        if kwargs is None:
            kwargs = {}
        args = (func,) + args
        
        def _callback(func, *a, **kw):
            self.wait()
            func(*a, **kw)
        t = threading.Thread(target=_callback, args=args, kwargs=kwargs)
        t.setName('Engine Callback ' + t.getName())
        t.start()
        
        self.start()
        
        return t
    
    def log(self, msg="", traceback=False):
        if traceback:
            msg = '\n'.join((msg, format_exc()))
        print msg


def format_exc(exc=None):
    """Return exc (or sys.exc_info if None), formatted."""
    if exc is None:
        exc = sys.exc_info()
    if exc == (None, None, None):
        return ""
    return "".join(traceback.format_exception(*exc))

