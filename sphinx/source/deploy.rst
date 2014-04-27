
Deploy
------

WSGI servers
############

Though CherryPy comes with a very reliable and fast enough HTTP server,
you may wish to integrate your CherryPy application within a 
different framework. To do so, we will benefit from the WSGI
interface.

Tornado
^^^^^^^

You can use `tornado <http://www.tornadoweb.org/>`_ HTTP server as 
follow:

.. code-block:: python

    import cherrypy

    class Root(object):
        @cherrypy.expose
        def index(self):
            return "Hello World!"

    if __name__ == '__main__':
        import tornado
        import tornado.httpserver
        import tornado.wsgi

        # our WSGI application
        wsgiapp = cherrypy.tree.mount(Root())

        # Disable the autoreload which won't play well 
        cherrypy.config.update({'engine.autoreload.on': False})

        # let's not start the CherryPy HTTP server
        cherrypy.server.unsubscribe()

        # use CherryPy's signal handling
        cherrypy.engine.signals.subscribe()

        # Prevent CherryPy logs to be propagated
        # to the Tornado logger
        cherrypy.log.error_log.propagate = False

        # Run the engine but don't block on it
        cherrypy.engine.start()

        # Run thr tornado stack
        container = tornado.wsgi.WSGIContainer(wsgiapp)
        http_server = tornado.httpserver.HTTPServer(container)
        http_server.listen(8080)
        # Publish to the CherryPy engine as if
        # we were using its mainloop
        tornado.ioloop.PeriodicCallback(lambda: cherrypy.engine.publish('main'), 100).start()
        tornado.ioloop.IOLoop.instance().start()

Twisted
^^^^^^^

You can use `Twisted <https://twistedmatrix.com/>`_ HTTP server as 
follow:

.. code-block:: python

    import cherrypy

    from twisted.web.wsgi import WSGIResource
    from twisted.internet import reactor
    from twisted.internet import task

    # Our CherryPy application
    class Root(object):
        @cherrypy.expose
        def index(self):
            return "hello world"

    # Create our WSGI app from the CherryPy application
    wsgiapp = cherrypy.tree.mount(Root())

    # Configure the CherryPy's app server
    # Disable the autoreload which won't play well 
    cherrypy.config.update({'engine.autoreload.on': False})

    # We will be using Twisted HTTP server so let's
    # disable the CherryPy's HTTP server entirely
    cherrypy.server.unsubscribe()

    # If you'd rather use CherryPy's signal handler
    # Uncomment the next line. I don't know how well this
    # will play with Twisted however
    #cherrypy.engine.signals.subscribe()

    # Publish periodically onto the 'main' channel as the bus mainloop would do
    task.LoopingCall(lambda: cherrypy.engine.publish('main')).start(0.1)

    # Tie our app to Twisted
    reactor.addSystemEventTrigger('after', 'startup', cherrypy.engine.start)
    reactor.addSystemEventTrigger('before', 'shutdown', cherrypy.engine.exit)
    resource = WSGIResource(reactor, reactor.getThreadPool(), wsgiapp)
		
Notice how we attach the bus methods to the Twisted's own lifecycle.

Save that code into a module named `cptw.py` and run it as follow:

.. code-block:: bash

   $ twistd -n web --port 8080 --wsgi cptw.wsgiapp


uwsgi
^^^^^

You can use `uwsgi <http://projects.unbit.it/uwsgi/>`_ HTTP server as 
follow:

.. code-block:: python

    import cherrypy

    # Our CherryPy application
    class Root(object):
        @cherrypy.expose
        def index(self):
            return "hello world"

    cherrypy.config.update({'engine.autoreload.on': False})
    cherrypy.server.unsubscribe()
    cherrypy.engine.start()

    wsgiapp = cherrypy.tree.mount(Root())

Save this into a Python module called `mymod.py` and run
it as follow:


.. code-block:: bash

   $ uwsgi --socket 127.0.0.1:8080 --protocol=http --wsgi-file mymod.py --callable wsgiapp


Virtual Hosting
###############

CherryPy has support for virtual-hosting. It does so through
a dispatchers that locate the appropriate resource based
on the requested domain.

Below is a simple example for it:

.. code-block:: python

    import cherrypy

    class Root(object):
        def __init__(self):
            self.app1 = App1()
            self.app2 = App2()

    class App1(object):
        @cherrypy.expose
        def index(self):
            return "Hello world from app1"

    class App2(object):
        @cherrypy.expose
        def index(self):
            return "Hello world from app2"

    if __name__ == '__main__':
        hostmap = {
            'company.com:8080': '/app1',
            'home.net:8080': '/app2',
        }

        config = {
            'request.dispatch': cherrypy.dispatch.VirtualHost(**hostmap)
        }

        cherrypy.quickstart(Root(), '/', {'/': config})

In this example, we declare two domains and their ports:

- company.com:8080
- home.net:8080

Thanks to the :class:`cherrypy.dispatch.VirtualHost` dispatcher, 
we tell CherryPy which application to dispatch to when a request 
arrives. The dispatcher looks up the requested domain and
call the according application.

.. note::

   To test this example, simply add the following rules to
   your `hosts` file:

   .. code-block:: text

      127.0.0.1       company.com
      127.0.0.1       home.net



Reverse-proxying
################

Apache
^^^^^^

Nginx
^^^^^

