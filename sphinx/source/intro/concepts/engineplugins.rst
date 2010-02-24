**************
Engine Plugins
**************

CherryPy allows you to extend startup, shutdown, and other behavior outside the
request process by defining *Plugins*. The ``cherrypy.engine`` object controls
these behaviors; to extend them, you subscribe plugins to the engine. Here's
the mechanism that gives you complete control over the subscription::

    engine.subscribe(channel, callback[, priority])

The channel is an event name, like "start", "stop", "exit", "graceful", or
"log". The callback is a function, class, or other callable. The optional
priority (0 - 100) allows multiple plugins to run in the correct order.

Most of the built-in plugins have their own ``subscribe`` method, so that
instead of writing the above, you write: ``p = Plugin(engine).subscribe()``.
That's it. If you want to turn off a plugin, call ``p.unsubscribe()``.
The plugin already knows the correct channel, callback, and priority.

Priorities of the built-in "start" listeners:

====================================================  ================
    Listener                                           Priority       
====================================================  ================
 default                                               50             
 :doc:`Daemonizer </progguide/daemonizer>`             65             
 :doc:`TimeoutMonitor </progguide/responsetimeouts>`   70             
 :doc:`Autoreloader </progguide/autoreloader>`         70             
 :ref:`pidfile`                                        70             
 :ref:`httpservers`                                    75             
 :ref:`dropprivileges`                                 77             
====================================================  ================

