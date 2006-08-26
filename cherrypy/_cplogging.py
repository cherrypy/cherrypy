"""CherryPy logging."""

import datetime
import logging
logfmt = logging.Formatter("%(message)s")
import os
import rfc822
import sys

import cherrypy
from cherrypy import _cperror


class LogManager(object):
    
    appid = None
    error_log = None
    access_log = None
    
    def __init__(self, appid=None):
        self.appid = appid
        if appid is None:
            self.error_log = logging.getLogger("cherrypy.error")
            self.access_log = logging.getLogger("cherrypy.access")
        else:
            self.error_log = logging.getLogger("cherrypy.error.%s" % appid)
            self.access_log = logging.getLogger("cherrypy.access.%s" % appid)
        self.error_log.setLevel(logging.DEBUG)
        self.access_log.setLevel(logging.INFO)
    
    def error(self, msg='', context='', severity=logging.DEBUG, traceback=False):
        """Write to the 'error' log.
        
        This is not just for errors! Applications may call this at any time
        to log application-specific information.
        """
        if traceback:
            msg += _cperror.format_exc()
        self.error_log.log(severity, ' '.join((self.time(), context, msg)))
    
    def __call__(self, *args, **kwargs):
        return self.error(*args, **kwargs)
    
    def access(self):
        """Write to the access log."""
        request = cherrypy.request
        response = cherrypy.response
        tmpl = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'
        s = tmpl % {'h': request.remote.name or request.remote.ip,
                    'l': '-',
                    'u': getattr(request, "login", None) or "-",
                    't': self.time(),
                    'r': request.request_line,
                    's': response.status.split(" ", 1)[0],
                    'b': response.headers.get('Content-Length', '') or "-",
                    'f': request.headers.get('referer', ''),
                    'a': request.headers.get('user-agent', ''),
                    }
        try:
            self.access_log.log(logging.INFO, s)
        except:
            self(traceback=True)
    
    def time(self):
        """Return now() in Apache Common Log Format (no timezone)."""
        now = datetime.datetime.now()
        month = rfc822._monthnames[now.month - 1].capitalize()
        return ('[%02d/%s/%04d:%02d:%02d:%02d]' %
                (now.day, month, now.year, now.hour, now.minute, now.second))
    
    def _get_builtin_handler(self, log, key):
        for h in log.handlers:
            if getattr(h, "_cpbuiltin", None) == key:
                return h
    
    
    # ------------------------- Screen handlers ------------------------- #
    
    def _set_screen_handler(self, log, enable):
        h = self._get_builtin_handler(log, "screen")
        if enable:
            if not h:
                h = logging.StreamHandler(sys.stdout)
                h.setLevel(logging.DEBUG)
                h.setFormatter(logfmt)
                h._cpbuiltin = "screen"
                log.addHandler(h)
        elif h:
            log.handlers.remove(h)
    
    def _get_screen(self):
        return (bool(self._get_builtin_handler(self.error_log, "screen")) or
                bool(self._get_builtin_handler(self.access_log, "screen")))
    def _set_screen(self, newvalue):
        self._set_screen_handler(self.error_log, newvalue)
        self._set_screen_handler(self.access_log, newvalue)
    screen = property(_get_screen, _set_screen)
    
    
    # -------------------------- File handlers -------------------------- #
    
    def _add_builtin_file_handler(self, log, fname):
        h = logging.FileHandler(fname)
        h.setLevel(logging.DEBUG)
        h.setFormatter(logfmt)
        h._cpbuiltin = "file"
        log.addHandler(h)
    
    def _set_file_handler(self, log, filename):
        h = self._get_builtin_handler(log, "file")
        if filename:
            if h:
                if h.baseFilename != os.path.abspath(filename):
                    h.close()
                    log.handlers.remove(h)
                    self._add_builtin_file_handler(log, filename)
            else:
                self._add_builtin_file_handler(log, filename)
        else:
            if h:
                h.close()
                log.handlers.remove(h)
    
    def _get_error_file(self):
        h = self._get_builtin_handler(self.error_log, "file")
        if h:
            return h.baseFilename
        return ''
    def _set_error_file(self, newvalue):
        self._set_file_handler(self.error_log, newvalue)
    error_file = property(_get_error_file, _set_error_file)
    
    def _get_access_file(self):
        h = self._get_builtin_handler(self.access_log, "file")
        if h:
            return h.baseFilename
        return ''
    def _set_access_file(self, newvalue):
        self._set_file_handler(self.access_log, newvalue)
    access_file = property(_get_access_file, _set_access_file)

