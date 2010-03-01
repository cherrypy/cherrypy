************
HTTP Servers
************

Starting in CherryPy 3.1, cherrypy.server is implemented as an
:ref:`Engine Plugin<plugins>`. It's
an instance of :class:`cherrypy._cpserver.Server`, which is a subclass of
:class:`cherrypy.process.servers.ServerAdapter`. The ``ServerAdapter`` class
is designed to control other servers, as well.

Multiple servers/ports
======================

If you need to start more than one HTTP server (to serve on multiple ports, or
protocols, etc.), you can manually register each one and then start them all
with engine.start::

    s1 = ServerAdapter(cherrypy.engine, MyWSGIServer(host='0.0.0.0', port=80))
    s2 = ServerAdapter(cherrypy.engine, another.HTTPServer(host='127.0.0.1', SSL=True))
    s1.subscribe()
    s2.subscribe()
    cherrypy.engine.start()

FastCGI/SCGI
============

There are also Flup'''F'''CGIServer and Flup'''S'''CGIServer classes in
process.servers. To start an fcgi server, for example, wrap an instance of it in
a ServerAdapter::

    addr = ('0.0.0.0', 4000)
    f = servers.FlupFCGIServer(application=cherrypy.tree, bindAddress=addr)
    s = servers.ServerAdapter(cherrypy.engine, httpserver=f, bind_addr=addr)
    s.subscribe()

Note that you need to download and install `flup <http://trac.saddi.com/flup>`_
yourself.
