
Deploy
------

CherryPy stands on its own, but as an application server, it is often
located in shared or complex environments. For this reason,
it is not uncommon to run CherryPy behind a reverse proxy
or use other servers to host the application.

.. note::

   CherryPy's server has proven reliable and fast enough
   for years now. If the volume of traffic you receive is
   average, it will do well enough on its own. Nonetheless,
   it is common to delegate the serving of static content
   to more capable servers such as `nginx <http://nginx.org>`_ or
   CDN.

.. contents::
   :depth:  3


Run as a daemon
###############

CherryPy allows you to easily decouple the current process from the parent
environment, using the traditional double-fork:

.. code-block:: python

   from cherrypy.process.plugins import Daemonizer
   d = Daemonizer(cherrypy.engine)
   d.subscribe()

.. note::

    This :ref:`engine plugin <busplugins>` is only available on
    Unix and similar systems which provide `fork()`.

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

Run as a different user
#######################

Use this :ref:`engine plugin <busplugins>` to start your
CherryPy site as root (for example, to listen on a privileged port like 80)
and then reduce privileges to something more restricted.

This priority of this plugin's "start" listener is slightly higher than the
priority for `server.start` in order to facilitate the most common use:
starting on a low port (which requires root) and then dropping to another user.

.. code-block:: python

   DropPrivileges(cherrypy.engine, uid=1000, gid=1000).subscribe()

PID files
#########

The PIDFile :ref:`engine plugin <busplugins>` is pretty straightforward: it writes
the process id to a file on start, and deletes the file on exit. You must
provide a 'pidfile' argument, preferably an absolute path:

.. code-block:: python

   PIDFile(cherrypy.engine, '/var/run/myapp.pid').subscribe()

Systemd socket activation
#########################

Socket Activation is a systemd feature that allows to setup a system so that
the systemd will sit on a port and start services 'on demand' (a little bit
like inetd and xinetd used to do).

CherryPy has built-in socket activation support, if run from a systemd
service file it will detect the `LISTEN_PID` environment variable to know that
it should consider fd 3 to be the passed socket.

To read more about socket activation:
http://0pointer.de/blog/projects/socket-activation.html

Control via Supervisord
#######################

`Supervisord <http://supervisord.org>`_ is a powerful process control
and management tool that can perform a lot of tasks around process monitoring.

Below is a simple supervisor configuration for your CherryPy
application.

.. code-block:: ini

   [unix_http_server]
   file=/tmp/supervisor.sock

   [supervisord]
   logfile=/tmp/supervisord.log ; (main log file;default $CWD/supervisord.log)
   logfile_maxbytes=50MB        ; (max main logfile bytes b4 rotation;default 50MB)
   logfile_backups=10           ; (num of main logfile rotation backups;default 10)
   loglevel=info                ; (log level;default info; others: debug,warn,trace)
   pidfile=/tmp/supervisord.pid ; (supervisord pidfile;default supervisord.pid)
   nodaemon=false               ; (start in foreground if true;default false)
   minfds=1024                  ; (min. avail startup file descriptors;default 1024)
   minprocs=200                 ; (min. avail process descriptors;default 200)

   [rpcinterface:supervisor]
   supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface

   [supervisorctl]
   serverurl=unix:///tmp/supervisor.sock

   [program:myapp]
   command=python server.py
   environment=PYTHONPATH=.
   directory=.

This could control your server via the ``server.py`` module as
the application entry point.

.. code-block:: python

   import cherrypy

   class Root(object):
       @cherrypy.expose
       def index(self):
           return "Hello World!"


   cherrypy.config.update({'server.socket_port': 8090,
                           'engine.autoreload.on': False,
                           'log.access_file': './access.log',
                           'log.error_file': './error.log'})
   cherrypy.quickstart(Root())

To take the configuration (assuming it was saved in a file
called ``supervisor.conf``) into account:

.. code-block:: bash

   $ supervisord -c supervisord.conf
   $ supervisorctl update

Now, you can point your browser at http://localhost:8090/
and it will display `Hello World!`.

To stop supervisor, type:

.. code-block:: bash

   $ supervisorctl shutdown

This will obviously shutdown your application.

.. _ssl:

SSL support
###########

.. note::

   You may want to test your server for SSL using the services
   from `Qualys, Inc. <https://www.ssllabs.com/ssltest/index.html>`_


CherryPy can encrypt connections using SSL to create an https connection. This keeps your web traffic secure. Here's how.

1. Generate a private key. We'll use openssl and follow the `OpenSSL Keys HOWTO <https://www.openssl.org/docs/HOWTO/keys.txt>`_.:

.. code-block:: bash

   $ openssl genrsa -out privkey.pem 2048

You can create either a key that requires a password to use, or one without a password. Protecting your private key with a password is much more secure, but requires that you enter the password every time you use the key. For example, you may have to enter the password when you start or restart your CherryPy server. This may or may not be feasible, depending on your setup.

If you want to require a password, add one of the ``-aes128``, ``-aes192`` or ``-aes256`` switches to the command above. You should not use any of the DES, 3DES, or SEED algorithms to protect your password, as they are insecure.

SSL Labs recommends using 2048-bit RSA keys for security (see references section at the end).


2. Generate a certificate. We'll use openssl and follow the `OpenSSL Certificates HOWTO <https://www.openssl.org/docs/HOWTO/certificates.txt>`_. Let's start off with a self-signed certificate for testing:

.. code-block:: bash

   $ openssl req -new -x509 -days 365 -key privkey.pem -out cert.pem

openssl will then ask you a series of questions. You can enter whatever values are applicable, or leave most fields blank. The one field you *must* fill in is the 'Common Name': enter the hostname you will use to access your site. If you are just creating a certificate to test on your own machine and you access the server by typing 'localhost' into your browser, enter the Common Name 'localhost'.


3. Decide whether you want to use python's built-in SSL library, or the pyOpenSSL library. CherryPy supports either.

    a) *Built-in.* To use python's built-in SSL, add the following line to your CherryPy config:

    .. code-block:: python

       cherrypy.server.ssl_module = 'builtin'

    b) *pyOpenSSL*. Because python did not have a built-in SSL library when CherryPy was first created, the default setting is to use pyOpenSSL. To use it you'll need to install it (we could recommend you install `cython <http://cython.org/>`_ first):

    .. code-block:: bash

       $ pip install cython, pyOpenSSL


4. Add the following lines in your CherryPy config to point to your certificate files:

.. code-block:: python

   cherrypy.server.ssl_certificate = "cert.pem"
   cherrypy.server.ssl_private_key = "privkey.pem"

5. If you have a certificate chain at hand, you can also specify it:

.. code-block:: python

   cherrypy.server.ssl_certificate_chain = "certchain.perm"

6. Start your CherryPy server normally. Note that if you are debugging locally and/or using a self-signed certificate, your browser may show you security warnings.

WSGI servers
############

Embedding into another WSGI framework
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Though CherryPy comes with a very reliable and fast enough HTTP server,
you may wish to integrate your CherryPy application within a
different framework. To do so, we will benefit from the WSGI
interface defined in :pep:`333` and :pep:`3333`.

Note that you should follow some basic rules when embedding CherryPy
in a third-party WSGI server:

- If you rely on the `"main"` channel to be published on, as
  it would happen within the CherryPy's mainloop, you should
  find a way to publish to it within the other framework's mainloop.

- Start the CherryPy's engine. This will publish to the `"start"` channel
  of the bus.

  .. code-block:: python

     cherrypy.engine.start()

- Stop the CherryPy's engine when you terminate. This will publish
  to the `"stop"` channel of the bus.

  .. code-block:: python

     cherrypy.engine.stop()

- Do not call ``cherrypy.engine.block()``.

- Disable the built-in HTTP server since it will not be used.

  .. code-block:: python

     cherrypy.server.unsubscribe()

- Disable autoreload. Usually other frameworks won't react well to it,
  or sometimes, provide the same feature.

  .. code-block:: python

     cherrypy.config.update({'engine.autoreload.on': False})

- Disable CherryPy signals handling. This may not be needed, it depends
  on how the other framework handles them.

  .. code-block:: python

     cherrypy.engine.signals.subscribe()

- Use the ``"embedded"`` environment configuration scheme.

  .. code-block:: python

     cherrypy.config.update({'environment': 'embedded'})

  Essentially this will disable the following:

  - Stdout logging
  - Autoreloader
  - Configuration checker
  - Headers logging on error
  - Tracebacks in error
  - Mismatched params error during dispatching
  - Signals (SIGHUP, SIGTERM)

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

Save that code into a module named `cptw.py` and run it as follows:

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
it as follows:


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

nginx is a fast and modern HTTP server with a small footprint. It is
a popular choice as a reverse proxy to application servers such as
CherryPy.

This section will not cover the whole range of features nginx provides.
Instead, it will simply provide you with a basic configuration that can
be a good starting point.


.. code-block:: nginx
   :linenos:

   upstream apps {
      server 127.0.0.1:8080;
      server 127.0.0.1:8081;
   }

   gzip_http_version 1.0;
   gzip_proxied      any;
   gzip_min_length   500;
   gzip_disable      "MSIE [1-6]\.";
   gzip_types        text/plain text/xml text/css
                     text/javascript
                     application/javascript;

   server {
      listen 80;
      server_name  www.example.com;

      access_log  /app/logs/www.example.com.log combined;
      error_log  /app/logs/www.example.com.log;

      location ^~ /static/  {
         root /app/static/;
      }

      location / {
         proxy_pass         http://apps;
         proxy_redirect     off;
         proxy_set_header   Host $host;
         proxy_set_header   X-Real-IP $remote_addr;
         proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
         proxy_set_header   X-Forwarded-Host $server_name;
      }
   }

Edit this configuration to match your own paths. Then, save this configuration
into a file under ``/etc/nginx/conf.d/`` (assuming Ubuntu).
The filename is irrelevant. Then run the following commands:

.. code-block:: bash

   $ sudo service nginx stop
   $ sudo service nginx start

Hopefully, this will be enough to forward requests hitting
the nginx frontend to your CherryPy application. The ``upstream``
block defines the addresses of your CherryPy instances.

It shows that you can load-balance between two application
servers. Refer to the nginx documentation to understand
how this achieved.

.. code-block:: nginx

   upstream apps {
      server 127.0.0.1:8080;
      server 127.0.0.1:8081;
   }

Later on, this block is used to define the reverse
proxy section.

Now, let's see our application:

.. code-block:: python

    import cherrypy

    class Root(object):
        @cherrypy.expose
        def index(self):
            return "hello world"

    if __name__ == '__main__':
        cherrypy.config.update({
            'server.socket_port': 8080,
            'tools.proxy.on': True,
            'tools.proxy.base': 'http://www.example.com'
        })
        cherrypy.quickstart(Root())

If you run two instances of this code, one on each
port defined in the nginx section, you will be able
to reach both of them via the load-balancing done
by nginx.

Notice how we define the proxy tool. It is not mandatory and
used only so that the CherryPy request knows about the true
client's address. Otherwise, it would know only about the
nginx's own address. This is most visible in the logs.

The ``base`` attribute should match the ``server_name``
section of the nginx configuration.
