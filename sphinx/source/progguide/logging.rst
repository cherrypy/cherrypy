
Logging
*******

CherryPy 3 uses the ``logging`` module from Python's standard library.

Simple config
=============

Although CherryPy uses the logging module, it does so "behind the scenes" so that simple logging is simple (but complicated logging is still possible). "Simple" logging means that you can log to the screen (i.e. console/stdout) or to a file, and that you can easily have separate error and access log files.

Here are the simplified logging settings. You use these by adding lines to your config file or dict. You should set these at either the global level or per application (see next), but generally not both.

 * log.screen: Set this to True to have both "error" and "access" messages printed to stdout.
 * log.access_file: Set this to an absolute filename where you want "access" messages written.
 * log.error_file: Set this to an absolute filename where you want "error" messages written.

Many events are automatically logged; to log your own application events, call ``cherrypy.log(msg, context='', severity=logging.DEBUG, traceback=False)``.

Architecture
============

Separate scopes
---------------

CherryPy provides log managers at '''both''' the global and application layers. This means you can have one set of logging rules for your entire site, and another set of rules specific to each application. The global log manager is found at ``cherrypy.log``, and the log manager for each application is found at ``app.log``. If you're inside a request, the latter is reachable from `cherrypy.request.app.log`; if you're outside a request, you'll have to obtain a reference to the `app`: either the return value of `tree.mount()` or, if you used `quickstart()` instead, via `cherrypy.tree.apps['/']`.

By default, the global logs are named "cherrypy.error" and "cherrypy.access", and the application logs are named "cherrypy.error.2378745" and "cherrypy.access.2378745" (the number is the id of the Application object). This means that the application logs "bubble up" to the site logs, so if your application has no log handlers, the site-level handlers will still log the messages.

Errors vs. Access
-----------------

Each log manager handles both "access" messages (one per HTTP request) and "error" messages (everything else). Note that the "error" log is not just for errors! The format of access messages is highly formalized, but the error log isn't--it receives messages from a variety of sources (including full error tracebacks, if enabled).

Log Manager Objects
-------------------

Each log manager possesses the following attributes:

 * access(): writes to the access log in `Apache/NCSA Combined Log Format <http://httpd.apache.org/docs/2.0/logs.html#combined>`_. CherryPy calls this automatically for you. Note there are no arguments; it collects the data itself from ``cherrypy.request``.
 * access_file: the filename for ``self.access_log``. If you set this to a string, it'll add the appropriate FileHandler for you. If you set it to None or ``''``, it will remove the handler.
 * access_log: the actual ``logging.Logger`` instance for access messages.
 * appid: the id of the Application object which owns this log manager. If this is a global log manager, appid is None.
 * ``__call__``: an alias for ``error`` (see next).
 * ``error(msg='', context='', severity=logging.DEBUG, traceback=False)``: write ''msg'' to the error log. If ''traceback'' is True, the traceback of the current exception (if any) will be appended to ''msg''.
 * error_file: the filename for ``self.error_log``. If you set this to a string, it'll add the appropriate FileHandler for you. If you set it to None or ``''``, it will remove the handler.
 * error_log: the actual ``logging.Logger`` instance for error messages.
 * logger_root: the "top-level" logger name ("<logger_root>.error.<appid>"). Defaults to "cherrypy".
 * screen: a boolean. If you set this to True, it'll add the appropriate ``StreamHandler(sys.stdout)`` for you. If you set it to False, it will remove the handler.
 * time(): returns now() in Apache Common Log Format (no timezone).
 * wsgi: a boolean. If you set this to True, it'll add the appropriate ``WSGIErrorHandler`` for you (which writes errors to ``wsgi.errors``). If you set it to False, it will remove the handler.


Custom Handlers
===============

The simple settings above work by manipulating Python's standard ``logging`` module. So when you need something more complex, the full power of the standard module is yours to exploit. You can borrow or create custom handlers, formats, filters, and much more. Here's an example that skips the standard FileHandler and uses a RotatingFileHandler instead:

::

    #python
    log = app.log
    
    # Remove the default FileHandlers if present.
    log.error_file = ""
    log.access_file = ""
    
    maxBytes = getattr(log, "rot_maxBytes", 10000000)
    backupCount = getattr(log, "rot_backupCount", 1000)
    
    # Make a new RotatingFileHandler for the error log.
    fname = getattr(log, "rot_error_file", "error.log")
    h = handlers.RotatingFileHandler(fname, 'a', maxBytes, backupCount)
    h.setLevel(DEBUG)
    h.setFormatter(_cplogging.logfmt)
    log.error_log.addHandler(h)
    
    # Make a new RotatingFileHandler for the access log.
    fname = getattr(log, "rot_access_file", "access.log")
    h = handlers.RotatingFileHandler(fname, 'a', maxBytes, backupCount)
    h.setLevel(DEBUG)
    h.setFormatter(_cplogging.logfmt)
    log.access_log.addHandler(h)


The ``rot_*`` attributes are pulled straight from the application log object. Since "log.*" config entries simply set attributes on the log object, you can add custom attributes to your heart's content. Note that these handlers are used ''instead'' of the default, simple handlers outlined above (so don't set the "log.error_file" config entry, for example).

