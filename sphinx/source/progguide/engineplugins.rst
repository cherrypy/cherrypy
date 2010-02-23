.. _engineplugins:

**************
Engine Plugins
**************

The ``cherrypy.engine`` object is a WebSiteProcessBus. To extend the behavior
of the bus, you subscribe ``plugins: engine.subscribe(channel, callback[, priority])``. 
The channel is an event name, like "start", "stop", "exit", "graceful", or
"log". The callback is a function, class, or other callable. The optional
priority (0 - 100) allows multiple plugins to run in the correct order.

Most of the built-in plugins have their own ``subscribe`` method, so that
instead of writing the above, you write: ``Plugin(engine).subscribe()``.
That's it. If you want to turn off a plugin, call ``plugin.unsubscribe()``.
The plugin already knows the correct channel, callback, and priority.

Priorities of the built-in "start" listeners:

======================  ================
    Listener            Priority
======================  ================
 default                50             
 :ref:`daemonizer`      65             
 :ref:`timeoutmonitor`  70             
 :ref:`autoreloader`    70             
 :ref:`pidfile`         70             
 :ref:`httpservers`     75             
 :ref:`dropprivileges`  77             
======================  ================


