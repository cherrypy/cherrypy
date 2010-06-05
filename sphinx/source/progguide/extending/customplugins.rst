**************
Custom Plugins
**************

CherryPy allows you to extend startup, shutdown, and other behavior outside the
request process via *Listeners* and *Plugins*. The
:class:`cherrypy.engine<cherrypy.process.wspbus.Bus>` object controls
these behaviors; to extend them, you subscribe listeners to the engine.
These allow you to run functions at a particular point in the
*site* process; for the *request* process, see :doc:`customtools` instead.

Listeners
=========

The engine is a publish-subscribe service; event handlers publish to various
*channels*, like "start", "stop", "exit", "graceful", or "log", and both
CherryPy and you can subscribe *listeners* for those messages::

    engine.subscribe(channel, callback[, priority])

channel
-------

The channel is an event name:

 * start: the Engine is starting for the first time, or has been stopped and is
   now restarting; listeners here should start up sockets, files, or other
   services and not return until they are ready to be used by clients or
   other parts of the site.
 * stop: the Engine is stopping; plugins should cleanly stop what they are
   doing and not return until they have finished cleaning up. This is called
   by :func:`cherrypy.engine.stop<cherrypy.process.wspbus.Bus.stop>`, and
   plugins should make every effort to stop and clean up in a fashion that
   permits them to be restarted via a "start" listener.
 * graceful: advises all listeners to reload, e.g. by closing any open files
   and reopening them.
 * exit: this is called by
   :func:`cherrypy.engine.exit<cherrypy.process.wspbus.Bus.exit>`,
   and advises plugins to prepare for process termination. Note that
   :func:`cherrypy.engine.exit<cherrypy.process.wspbus.Bus.exit>` first calls
   :func:`cherrypy.engine.stop<cherrypy.process.wspbus.Bus.stop>`, so Plugins
   may expect to stop first, then exit in a separate step.
 * log(msg, level): in general, :class:`cherrypy.log<cherrypy._cplogging.LogManager>`
   listens on this channel. Plugins, however, should make every effort to
   publish to this channel verbosely to aid process event debugging. See the
   builtin Plugins for good examples.
 * main: New in 3.2. All Engine tasks run in threads other than the main thread;
   the main thread usually calls
   :func:`cherrypy.engine.block<cherrypy.process.wspbus.Bus.block>` to wait
   for KeyboardInterrupt and other signals. While blocked, it loops
   (every 1/10th of a second, by default), and publishes a message on the
   "main" channel each time. Listeners subscribed to this channel, therefore,
   are called at every interval.

callback
--------

The functionality you wish to run; this can be any function, class, or other
callable. Each channel defines the arguments; currently, however, only the "log"
channel defines any ('msg', the string message to log, and 'level', an int
following the levels defined in the stdlib's :mod:`logging <logging>` module).

priority
--------

The optional priority (0 - 100) allows multiple listeners to run in the correct
order. Lower numbers run first. The default is 50.

If you omit the priority argument to engine.subscribe (or pass ``None``),
you can instead set it as an attribute on the callback function::

    def setup_db():
        ....
    setup_db.priority = 90
    engine.subscribe('start', setup_db)


Plugins
=======

You can manually subscribe bus listeners, but you probably shouldn't.
*Plugins* allow your function to be subscribed and configured both
via the CherryPy config system and via the Plugin itself. Plugins also allow
you to write a single class that listens on multiple channels.

Most of the built-in plugins have their own ``subscribe`` method,
so that instead of writing ``engine.subscribe``, you write:
``p = Plugin(engine).subscribe()``. If you want to turn off a plugin,
call ``p.unsubscribe()``. The plugin already knows the correct channel,
callback, and priority.

You can run arbitrary code at any of the events by creating a
SimplePlugin object, with one method for each *channel* you wish to handle::

    class ScratchDB(plugins.SimplePlugin):
        
        def start(self):
            self.fname = 'myapp_%d.db' % os.getpid()
            self.db = sqlite.connect(database=self.fname)
        start.priority = 80
        
        def stop(self):
            self.db.close()
            os.remove(self.fname)
    cherrypy.engine.scratchdb = ScratchDB(cherrypy.engine)

...then, once you've authored your Plugin, turn it on by calling its
``subscribe`` method::

    cherrypy.engine.scratchdb.subscribe()

...or, in CherryPy 3.2 and above, in site config::

    [global]
    engine.scratchdb.on = True


Priorities of the built-in "start" listeners:

=====================================================  ================
 Listener                                              Priority        
=====================================================  ================
 default                                               50              
 :doc:`Daemonizer </deployguide/daemonizer>`           65              
 :doc:`Timeout Monitor </progguide/responsetimeouts>`  70              
 :doc:`Autoreloader </progguide/autoreloader>`         70              
 :doc:`PID File </deployguide/pidfile>`                70              
 :doc:`HTTP Servers </deployguide/httpservers>`        75              
 :doc:`Drop Privileges </deployguide/dropprivileges>`  77              
=====================================================  ================

