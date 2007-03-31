"""Windows service for restsrv. Requires pywin32."""

import thread
import win32api
import win32con
import win32event
import win32service
import win32serviceutil

from cherrypy.restsrv import base


class Engine(base.Engine):
    
    def __init__(self):
        base.Engine.__init__(self)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        win32api.SetConsoleCtrlHandler(self.console_event)
    
    def console_event(self, event):
        if event in (win32con.CTRL_C_EVENT,
                     win32con.CTRL_BREAK_EVENT,
                     win32con.CTRL_CLOSE_EVENT):
            self.log('Console event %s: shutting down engine' % event)
            self.stop()
            return 1
        return 0
    
    def block(self, interval=1):
        """Block forever (wait for stop(), KeyboardInterrupt or SystemExit)."""
        try:
            win32event.WaitForSingleObject(self.stop_event, win32event.INFINITE)
        except SystemExit:
            self.log('SystemExit raised: shutting down engine')
            self.stop()
            raise
    
    def stop(self):
        """Stop the engine."""
        if self.state != base.STOPPED:
            self.log('Engine shutting down')
            self.publish('stop')
            win32event.PulseEvent(self.stop_event)
            self.state = base.STOPPED


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
        restsrv.engine.start()
        restsrv.engine.block()
    
    def SvcStop(self):
        from cherrypy import restsrv
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        restsrv.engine.stop()
    
    def SvcOther(self, control):
        restsrv.engine.publish(control_codes.key_for(control))


if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(PyWebService)
