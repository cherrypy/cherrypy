****************
Handling Signals
****************

SignalHandler
=============

This :ref:`Engine Plugin<plugins>` is instantiated automatically as
``cherrypy.engine.signal_handler``.
However, it is only *subscribed* automatically by ``cherrypy.quickstart()``.
So if you want signal handling and you're calling:: 

    tree.mount(); engine.start(); engine.block()

on your own, be sure to add::

    if hasattr(cherrypy.engine, 'signal_handler'):
        cherrypy.engine.signal_handler.subscribe()

.. currentmodule:: cherrypy.process.plugins

.. autoclass:: SignalHandler
   :members:


.. index:: Windows, Ctrl-C, shutdown
.. _windows-console:

Windows Console Events
======================

Microsoft Windows uses console events to communicate some signals, like Ctrl-C.
When deploying CherryPy on Windows platforms, you should obtain the
`Python for Windows Extensions <http://sourceforge.net/projects/pywin32/>`_;
once you have them installed, CherryPy will handle Ctrl-C and other
console events (CTRL_C_EVENT, CTRL_LOGOFF_EVENT, CTRL_BREAK_EVENT,
CTRL_SHUTDOWN_EVENT, and CTRL_CLOSE_EVENT) automatically, shutting down the
bus in preparation for process exit.

