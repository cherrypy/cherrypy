"""Windows service for restsrv. Requires pywin32."""

import thread
import win32api
import win32con
import win32event
import win32service
import win32serviceutil

from cherrypy.restsrv import wspbus


class Win32Bus(wspbus.Bus):
    """A Web Site Process Bus implementation for Win32.
    
    Instead of using time.sleep for blocking, this bus uses native
    win32event objects.
    """
    
    def __init__(self):
        self.events = {}
        result = win32api.SetConsoleCtrlHandler(self._console_event, 1)
        if result == 0:
            self.log('Could not SetConsoleCtrlHandler (error %r)' %
                     win32api.GetLastError())
        wspbus.Bus.__init__(self)
    
    def _console_event(self, event):
        """The handler for console control events (like Ctrl-C)."""
        if event in (win32con.CTRL_C_EVENT, win32con.CTRL_LOGOFF_EVENT,
                     win32con.CTRL_BREAK_EVENT, win32con.CTRL_SHUTDOWN_EVENT,
                     win32con.CTRL_CLOSE_EVENT):
            self.log('Console event %s: shutting down bus' % event)
            
            # Remove this CtrlHandler so repeated Ctrl-C doesn't re-call it.
            try:
                result = win32api.SetConsoleCtrlHandler(self._console_event, 0)
                if result == 0:
                    self.log('Could not remove SetConsoleCtrlHandler (error %r)' %
                             win32api.GetLastError())
            except ValueError:
                pass
            
            self.stop()
            # 'First to return True stops the calls'
            return 1
        return 0
    
    def _get_state_event(self, state):
        """Return a win32event for the given state (creating it if needed)."""
        try:
            return self.events[state]
        except KeyError:
            event = win32event.CreateEvent(None, 0, 0, None)
            self.events[state] = event
            return event
    
    def _get_state(self):
        return self._state
    def _set_state(self, value):
        self._state = value
        event = self._get_state_event(value)
        win32event.PulseEvent(event)
    state = property(_get_state, _set_state)
    
    def block(self, state=wspbus.states.STOPPED, interval=1):
        """Wait for the given state, KeyboardInterrupt or SystemExit.
        
        Since this class uses native win32event objects, the interval
        argument is ignored.
        """
        event = self._get_state_event(state)
        try:
            win32event.WaitForSingleObject(event, win32event.INFINITE)
        except SystemExit:
            self.log('SystemExit raised: shutting down bus')
            self.stop()
            raise


class _ControlCodes(dict):
    """Control codes used to "signal" a service via ControlService.
    
    User-defined control codes are in the range 128-255. We generally use
    the standard Python value for the Linux signal and add 128. Example:
    
        >>> signal.SIGUSR1
        10
        control_codes['graceful'] = 128 + 10
    """
    
    def key_for(self, obj):
        """For the given value, return its corresponding key."""
        for key, val in self.iteritems():
            if val is obj:
                return key
        raise ValueError("The given object could not be found: %r" % obj)

control_codes = _ControlCodes({'graceful': 138})


def signal_child(service, command):
    if command == 'stop':
        win32serviceutil.StopService(service)
    elif command == 'restart':
        win32serviceutil.RestartService(service)
    else:
        win32serviceutil.ControlService(service, control_codes[command])


class PyWebService(win32serviceutil.ServiceFramework):
    """Python Web Service."""
    
    _svc_name_ = "Python Web Service"
    _svc_display_name_ = "Python Web Service"
    _svc_deps_ = None        # sequence of service names on which this depends
    _exe_name_ = "restsrv"
    _exe_args_ = None        # Default to no arguments
    
    # Only exists on Windows 2000 or later, ignored on windows NT
    _svc_description_ = "Python Web Service"
    
    def SvcDoRun(self):
        from cherrypy import restsrv
        restsrv.bus.start()
        restsrv.bus.block()
    
    def SvcStop(self):
        from cherrypy import restsrv
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        restsrv.bus.stop()
    
    def SvcOther(self, control):
        restsrv.bus.publish(control_codes.key_for(control))


if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(PyWebService)
