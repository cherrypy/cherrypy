****************
Handling Signals
****************

SignalHandler
=============

This plugin is instantiated automatically as ``cherrypy.engine.signal_handler``.
However, it is only *subscribed* automatically by ``cherrypy.quickstart()``. So if
you want signal handling and you're calling:: 

    tree.mount(); engine.start(); engine.block()

on your own, be sure to add::

    if hasattr(cherrypy.engine, 'signal_handler'):
        cherrypy.engine.signal_handler.subscribe()

You can modify what signals your application listens for, and what it does when
it receives signals, by modifying ``SignalHandler.handlers``, a dict of {signal
name: callback} pairs. The default set is::

    handlers = {'SIGTERM': self.bus.exit,
                'SIGHUP': self.handle_SIGHUP,
                'SIGUSR1': self.bus.graceful,
               }

The ``handle_SIGHUP`` method calls ``bus.restart()`` if the process is daemonized, but
``bus.exit()`` if the process is attached to a TTY. This is because Unix window
managers tend to send SIGHUP to terminal windows when the user closes them.

Feel free to add signals which are not available on every platform. The
``SignalHandler`` will ignore errors raised from attempting to register handlers
for unknown signals.


.. index:: Windows, Ctrl-C, shutdown
.. _windows-console:

Windows Console Events
======================

Microsoft Windows uses console events to communicate some signals, like Ctrl-C.
When deploying CherryPy on Windows platforms, you should obtain the
`Python for Windows Extensions <http://sourceforge.net/projects/pywin32/>`_;
once you have them installed, CherryPy will automatically handle Ctrl-C and
other console events (CTRL_C_EVENT, CTRL_LOGOFF_EVENT, CTRL_BREAK_EVENT,
CTRL_SHUTDOWN_EVENT, and CTRL_CLOSE_EVENT) automatically, shutting down the
bus in preparation for process exit.

