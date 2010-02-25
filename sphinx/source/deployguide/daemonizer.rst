***************
Run as a daemon
***************

CherryPy allows you to easily decouple the current process from the parent
environment, using the traditional double-fork::

    from cherrypy.process.plugins import Daemonizer
    d = Daemonizer(cherrypy.engine)
    d.subscribe()

.. note::

    This :doc:`plugin </intro/concepts/engineplugins>` is only available on
    Unix and similar systems which provide fork().

If a startup error occurs in the forked children, the return code from the
parent process will still be 0. Errors in the initial daemonizing process still
return proper exit codes, but errors after the fork won't. Therefore, if you use
this plugin to daemonize, don't use the return code as an accurate indicator of
whether the process fully started. In fact, that return code only indicates if
the process successfully finished the first fork.

The plugin takes optional arguments to redirect standard streams: ``stdin``,
``stdout``, and ``stderr``. By default, these are all redirected to
:file:`/dev/null`, but you're free to send them to log files or elsewhere.

.. warning::

    You should be careful to not start any threads before this plugin runs.
    The plugin will warn if you do so, because "...the effects of calling functions
    that require certain resources between the call to fork() and the call to an
    exec function are undefined". (`ref <http://www.opengroup.org/onlinepubs/000095399/functions/fork.html>`_).
    It is for this reason that the Server plugin runs at priority 75 (it starts
    worker threads), which is later than the default priority of 65 for the
    Daemonizer.

