*******************
The CherryPy Engine
*******************

The :class:`cherrypy.engine<cherrypy.process.wspbus.Bus>` object contains and
manages site-wide behavior: daemonization, HTTP server start/stop, process
reload, signal handling, drop privileges, PID file management, logging for
all of these, and many more.

Any task that needs to happen outside of the request process is managed by
the Engine via *Plugins*. You can add your own site-wide
behaviors, too; see :doc:`/progguide/extending/customplugins`. The Engine
handles these tasks whether you start your site from a script, from an external
server process like Apache, or via :doc:`cherryd</deployguide/cherryd>`.

State Management
================

The Engine manages the *state* of the site. Engine methods like
:func:`cherrypy.engine.start<cherrypy.process.wspbus.start>` move it
from one state to another::

                        O
                        |
                        V
       STOPPING --> STOPPED --> EXITING -> X
          A   A         |
          |    \___     |
          |        \    |
          |         V   V
        STARTED <-- STARTING

Note in particular that the Engine allows you to stop and restart it again
without stopping the process. This can be used to build highly dynamic sites,
and is invaluable for debugging live servers.

Channels
========

The Engine uses topic-based publish-subscribe messaging to manage event-driven
behaviors like autoreload and daemonization. When the Engine moves from one
state to another, it *publishes* a message on a *channel* named after the
activity. For example, when you call
:func:`cherrypy.engine.start<cherrypy.process.wspbus.start>`, the Engine
moves from the STOPPED state to the STARTING state, publishes a message on
the "start" *channel*, and then moves to the STARTED state.

.. _plugins:

Plugins
=======

Engine Plugins package up channel listeners into easy-to-use components.

Engine Plugins have a :func:`subscribe<cherrypy.process.plugins.SimplePlugin.subscribe>`
method which you can use to "turn them on"; that is, they will start listening
for messages published on event channels. For example, to turn on PID file
management::

    from cherrypy.process.plugins import PIDFile
    p = PIDFile(cherrypy.engine, "/var/run/myapp.pid")
    p.subscribe()

If you want to turn off a plugin, call ``p.unsubscribe()``.

The following builtin plugins are subscribed by default:

 * :doc:`Timeout Monitor</progguide/responsetimeouts>`
 * :doc:`Autoreload</progguide/autoreloader>` (off in the "production" :ref:`environment<environments>`)
 * :class:`cherrypy.server<cherrypy._cpserver.Server>`
 * :class:`cherrypy.checker<cherrypy._cpchecker.Checker>`
 * Engine log messages go to :class:`cherrypy.log<cherrypy._GlobalLogManager>`.
 * A :doc:`Signal Handler</deployguide/signalhandler>`.

