*******************************
Your first CherryPy application
*******************************

The standard 'Hello world!' application takes less than 10 lines of code
when written using CherryPy::

    import cherrypy

    class HelloWorld:
        def index(self):
            return "Hello world!"
        index.exposed = True

    cherrypy.quickstart(HelloWorld())

We assume that you already have :doc:`installed </intro/install>` CherryPy.
Copy the file above and save it locally as ``hello.py``, then start the
application at the command prompt::

    $ python hello.py

Direct your favorite web browser to http://localhost:8080 and you should
see ``Hello world!`` printed there.

How does it work?
-----------------

Let's take a look at ``hello.py``:

 * The ``import cherrypy`` statement imports the main CherryPy module.
   This is all that is required to have CherryPy working. Feel free to
   "import cherrypy" in an interactive session and see what's available!
   ``help(cherrypy)`` is also quite useful.
 * We declare a class named ``HelloWorld``. An instance of this class is the
   object that will be published by CherryPy. It contains a single method,
   named ``index``, which will get called when the root URL for the site is
   requested (for example, ``http://localhost/``). This method returns the
   **contents** of the Web page; in this case, the ``'Hello World!'`` string.
   Note that you don't have to subclass any framework-provided classes; in fact,
   you don't even have to use classes at all! But let's start with them for now.
 * The ``index.exposed = True`` is a necessary step to tell CherryPy that the
   ``index()`` method will be **exposed**. Only exposed methods can be called
   to answer a request. This feature allows the user to select which methods
   of an object will be accessible via the Web; non-exposed methods can't be
   accessed.
 * ``cherrypy.quickstart(HelloWorld())`` mounts an instance of the HelloWorld
   class, and starts the embedded webserver. It runs until explicitly
   interrupted, either with ``Ctrl-C`` or via a suitable signal (a simple
   ``kill`` on Unix will do it).

When the application is executed, the CherryPy server is started with the
default configuration. It will listen on ``localhost`` at port ``8080``. These
defaults can be overridden by using a configuration file or dictionary
(more on this later).

Finally, the web server receives the request for the URL
``http://localhost:8080``. It searches for the best method to handle the
request, starting from the ``HelloWorld`` instance. In this particular case,
the root of the site is automatically mapped to the ``index()`` method (similar
to the ``index.html`` that is the standard page for conventional Web servers).
The HelloWorld class defines an ``index()`` method and exposes it. CherryPy
calls ``HelloWorld().index()``, and the result of the call is sent back to
the browser as the contents of the index page for the website. All the
dispatching and HTTP-processing work is
done automatically; the application programmer only needs to provide the
desired content as the return value of the ``index`` method.

CherryPy structure
------------------

Most of the features of CherryPy are available through the :mod:`cherrypy`
module. It contains several members:

 * :class:`cherrypy.engine <cherrypy.process.wspbus.Bus>`
   controls process startup, shutdown, and other events, including your own
   Plugins. See :doc:`/concepts/engine`.
 * :class:`cherrypy.server <cherrypy._cpserver.Server>` configures and controls
   the HTTP server.
 * :class:`cherrypy.request <cherrypy._cprequest.Request>` contains all
   the information that comes with the HTTP request, after it is parsed and
   analyzed by CherryPy.
 * :attr:`cherrypy.request.headers <cherrypy.lib.httputil.HeaderMap>`
   contains a mapping with the header options that were sent as part of
   the request.
 * :class:`cherrypy.session <cherrypy.lib.sessions.Session>` is a special
   mapping that is automatically generated and encoded by CherryPy; it can
   be used to store session-data in a persistent cookie. For it to work you
   have to enable the session functionality by setting 'tools.session.on' to
   True in your config.
 * :class:`cherrypy.response <cherrypy._cprequest.Response>` contains the
   data that is used to build the HTTP response.
 * :attr:`cherrypy.response.headers <cherrypy.lib.httputil.HeaderMap>`
   contains a mapping with the header options that will be returned by the
   server, before the contents get sent.
 * :attr:`cherrypy.response.body <cherrypy._cprequest.Response.body>` contains
   the actual contents of the webpage that will be sent as a response.

CherryPy Response
-----------------

The `cherrypy.response` object is available to affect aspects of the response
to a request. Like the request, the response object is a thread-local,
meaning although it appears to be a global variable, its value is specific
to the current thread, and thus the current request.

One may store arbitrary data in the response object.

HTTP Headers
------------

CherryPy exposes the request headers (as sent from the client), and response
headers (to be returned in the response) in the `headers` attribute of
`cherrypy.request` and `cherrypy.response`.

For example, to find out what "host" to which the client intended to connect::

    @cherrypy.expose
    def index(self):
        host = cherrypy.request.headers('Host')
        return "You have successfully reached " + host

Or to set headers on the response::

    @cherrypy.expose
    def index(self):
        cherrypy.response.headers['Content-Type'] = 'application/jpeg'
        return my_jpeg_data()
