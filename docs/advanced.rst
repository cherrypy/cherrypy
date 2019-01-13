.. _advanced:

Advanced
--------

CherryPy has support for more advanced features that these sections
will describe.

.. contents::
   :depth:  4

.. _aliases:

Set aliases to page handlers
############################

A fairly unknown, yet useful, feature provided by the :func:`cherrypy.expose`
decorator is to support aliases.

Let's use the template provided by :ref:`tutorial 03 <tut03>`:

.. code-block:: python

   import random
   import string

   import cherrypy

   class StringGenerator(object):
       @cherrypy.expose(['generer', 'generar'])
       def generate(self, length=8):
           return ''.join(random.sample(string.hexdigits, int(length)))

   if __name__ == '__main__':
       cherrypy.quickstart(StringGenerator())

In this example, we create localized aliases for
the page handler. This means the page handler will be
accessible via:

- /generate
- /generer (French)
- /generar (Spanish)

Obviously, your aliases may be whatever suits your needs.

.. note::

   The alias may be a single string or a list of them.

.. _restful:

RESTful-style dispatching
#########################

The term `RESTful URL` is sometimes used to talk about friendly URLs
that nicely map to the entities an application exposes.

.. important::

   We will not enter the debate around what is restful or not but we will
   showcase two mechanisms to implement the usual idea in your
   CherryPy application.

Let's assume you wish to create an application that exposes
music bands and their records. Your application will probably have
the following URLs:

- http://hostname/<artist>/
- http://hostname/<artist>/albums/<album_title>/

It's quite clear you would not create a page handler named after
every possible band in the world. This means you will need a page handler
that acts as a proxy for all of them.

The default dispatcher cannot deal with that scenario on its own
because it expects page handlers to be explicitly declared in your
source code. Luckily, CherryPy provides ways to support those use cases.

.. seealso::

   This section extends from this `stackoverflow response <http://stackoverflow.com/a/15789415/1363905>`_.

The special _cp_dispatch method
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``_cp_dispatch`` is a special method you declare in any of your :term:`controller`
to massage the remaining segments before CherryPy gets to process them.
This offers you the capacity to remove, add or otherwise handle any segment
you wish and, even, entirely change the remaining parts.

.. code-block:: python

    import cherrypy

    class Band(object):
        def __init__(self):
            self.albums = Album()

        def _cp_dispatch(self, vpath):
            if len(vpath) == 1:
                cherrypy.request.params['name'] = vpath.pop()
                return self

            if len(vpath) == 3:
                cherrypy.request.params['artist'] = vpath.pop(0)  # /band name/
                vpath.pop(0) # /albums/
                cherrypy.request.params['title'] = vpath.pop(0) # /album title/
                return self.albums

            return vpath

        @cherrypy.expose
        def index(self, name):
            return 'About %s...' % name

    class Album(object):
        @cherrypy.expose
        def index(self, artist, title):
            return 'About %s by %s...' % (title, artist)

    if __name__ == '__main__':
        cherrypy.quickstart(Band())

Notice how the controller defines `_cp_dispatch`, it takes
a single argument, the URL path info broken into its segments.

The method can inspect and manipulate the list of segments,
removing any or adding new segments at any position. The new list of
segments is then sent to the dispatcher which will use it
to locate the appropriate resource.

In the above example, you should be able to go to the following URLs:

- http://localhost:8080/nirvana/
- http://localhost:8080/nirvana/albums/nevermind/

The ``/nirvana/`` segment is associated to the band and
the ``/nevermind/`` segment relates to the album.

To achieve this, our `_cp_dispatch` method works on the idea
that the default dispatcher matches URLs against page handler
signatures and their position in the tree of handlers.

In this case, we take the dynamic segments in the URL (band and record names),
we inject them into the request parameters and we remove them
from the segment lists as if they had never been there in the first place.

In other words, `_cp_dispatch` makes it as if we were
working on the following URLs:

- http://localhost:8080/?artist=nirvana
- http://localhost:8080/albums/?artist=nirvana&title=nevermind


The popargs decorator
^^^^^^^^^^^^^^^^^^^^^

:func:`cherrypy.popargs` is more straightforward as it gives a name to any segment
that CherryPy wouldn't be able to interpret otherwise. This makes the
matching of segments with page handler signatures easier and helps CherryPy
understand the structure of your URL.

.. code-block:: python

    import cherrypy

    @cherrypy.popargs('band_name')
    class Band(object):
        def __init__(self):
            self.albums = Album()

        @cherrypy.expose
        def index(self, band_name):
            return 'About %s...' % band_name

    @cherrypy.popargs('album_title')
    class Album(object):
        @cherrypy.expose
        def index(self, band_name, album_title):
            return 'About %s by %s...' % (album_title, band_name)

    if __name__ == '__main__':
        cherrypy.quickstart(Band())

This works similarly to `_cp_dispatch` but, as said above, is more
explicit and localized. It says:

- take the first segment and store it into a parameter named `band_name`
- take again the first segment (since we removed the previous first)
  and store it into a parameter named `album_title`

Note that the decorator accepts more than a single binding. For instance:

.. code-block:: python

    @cherrypy.popargs('album_title')
    class Album(object):
        def __init__(self):
            self.tracks = Track()

    @cherrypy.popargs('track_num', 'track_title')
    class Track(object):
        @cherrypy.expose
        def index(self, band_name, album_title, track_num, track_title):
            ...

This would handle the following URL:

- http://localhost:8080/nirvana/albums/nevermind/tracks/06/polly

Notice finally how the whole stack of segments is passed to each
page handler so that you have the full context.

Error handling
##############
CherryPy's ``HTTPError`` class supports raising immediate responses in the case of
errors.

.. code-block:: python

    class Root:
        @cherrypy.expose
        def thing(self, path):
            if not authorized():
                raise cherrypy.HTTPError(401, 'Unauthorized')
            try:
                file = open(path)
            except FileNotFoundError:
                raise cherrypy.HTTPError(404)

``HTTPError.handle`` is a context manager which supports translating exceptions
raised in the app into an appropriate HTTP response, as in the second example.

.. code-block:: python

    class Root:
        @cherrypy.expose
        def thing(self, path):
            with cherrypy.HTTPError.handle(FileNotFoundError, 404):
                file = open(path)

Streaming the response body
###########################

CherryPy handles HTTP requests, packing and unpacking the low-level details,
then passing control to your application's :term:`page handler`, which produce
the body of the response. CherryPy allows you to return body content in a
variety of types: a string, a list of strings, a file. CherryPy also allows you
to *yield* content, rather than *return* content. When you use "yield", you also
have the option of streaming the output.

**In general, it is safer and easier to not stream output.** Therefore,
streaming output is off by default. Streaming output and also using sessions
requires a good understanding of :py:mod:`how session locks work
<cherrypy.lib.sessions>`.

The "normal" CherryPy response process
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When you provide content from your page handler, CherryPy manages the
conversation between the HTTP server and your code like this:

.. image:: _static/images/cpreturn.gif

Notice that the HTTP server gathers all output first and then writes everything
to the client at once: status, headers, and body. This works well for static or
simple pages, since the entire response can be changed at any time, either in
your application code, or by the CherryPy framework.

How "streaming output" works with CherryPy
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When you set the config entry "response.stream" to True (and use "yield"),
CherryPy manages the conversation between the HTTP server and your code like this:

.. image:: _static/images/cpyield.gif

When you stream, your application doesn't immediately pass raw body content
back to CherryPy or to the HTTP server. Instead, it passes back a generator.
At that point, CherryPy finalizes the status and headers, **before** the
generator has been consumed, or has produced any output. This is necessary to
allow the HTTP server to send the headers and pieces of the body as they become
available.

Once CherryPy has set the status and headers, it sends them to the HTTP server,
which then writes them out to the client. From that point on, the CherryPy
framework mostly steps out of the way, and the HTTP server essentially requests
content directly from your application code (your page handler method).

Therefore, when streaming, if an error occurs within your page handler,
CherryPy will not catch it--the HTTP server will catch it. Because the headers
(and potentially some of the body) have already been written to the client,
the server *cannot* know a safe means of handling the error, and will therefore
simply close the connection (the current, builtin servers actually write out a
short error message in the body, but this may be changed, and is not guaranteed
behavior for all HTTP servers you might use with CherryPy).

In addition, you cannot manually modify the status or headers within your page
handler if that handler method is a streaming generator, because the method will
not be iterated over until after the headers have been written to the client.
**This includes raising exceptions like HTTPError, NotFound, InternalRedirect
and HTTPRedirect.** To use a streaming generator while modifying headers, you
would have to return a generator that is separate from (or embedded in) your
page handler. For example:

.. code-block:: python

    class Root:
        @cherrypy.expose
        def thing(self):
            cherrypy.response.headers['Content-Type'] = 'text/plain'
            if not authorized():
                raise cherrypy.NotFound()
            def content():
                yield "Hello, "
                yield "world"
            return content()
        thing._cp_config = {'response.stream': True}

Streaming generators are sexy, but they play havoc with HTTP. CherryPy allows
you to stream output for specific situations: pages which take many minutes to
produce, or pages which need a portion of their content immediately output to
the client. Because of the issues outlined above, **it is usually better to
flatten (buffer) content rather than stream content**. Do otherwise only when
the benefits of streaming outweigh the risks.

Response timing
###############

CherryPy responses include an attribute:

 * ``response.time``: the :func:`time.time` at which the response began

Deal with signals
#################

This :ref:`engine plugin <busplugins>` is instantiated automatically as
`cherrypy.engine.signal_handler`.
However, it is only *subscribed* automatically by :func:`cherrypy.quickstart`.
So if you want signal handling and you're calling:

.. code-block:: python

   tree.mount()
   engine.start()
   engine.block()

on your own, be sure to add before you start the engine:

.. code-block:: python

   engine.signals.subscribe()

.. index:: Windows, Ctrl-C, shutdown
.. _windows-console:

Windows Console Events
^^^^^^^^^^^^^^^^^^^^^^

Microsoft Windows uses console events to communicate some signals, like Ctrl-C.
Deploying CherryPy on Windows platforms requires `Python for Windows Extensions
<http://sourceforge.net/projects/pywin32/>`_, which are installed automatically,
being provided an extra dependency with environment marker. With that
installed, CherryPy will handle Ctrl-C and other
console events (CTRL_C_EVENT, CTRL_LOGOFF_EVENT, CTRL_BREAK_EVENT,
CTRL_SHUTDOWN_EVENT, and CTRL_CLOSE_EVENT) automatically, shutting down the
bus in preparation for process exit.


Securing your server
####################

.. note::

   This section is not meant as a complete guide to securing
   a web application or ecosystem. Please review the various
   guides provided at `OWASP <https://www.owasp.org/index.php/Main_Page>`_.


There are several settings that can be enabled to make CherryPy pages more secure. These include:

    Transmitting data:

        #. Use Secure Cookies

    Rendering pages:

        #. Set HttpOnly cookies
        #. Set XFrame options
        #. Enable XSS Protection
        #. Set the Content Security Policy

An easy way to accomplish this is to set headers with a tool
and wrap your entire CherryPy application with it:

.. code-block:: python

   import cherrypy

   # set the priority according to your needs if you are hooking something
   # else on the 'before_finalize' hook point.
   @cherrypy.tools.register('before_finalize', priority=60)
   def secureheaders():
       headers = cherrypy.response.headers
       headers['X-Frame-Options'] = 'DENY'
       headers['X-XSS-Protection'] = '1; mode=block'
       headers['Content-Security-Policy'] = "default-src 'self';"

.. note::

   Read more about `those headers <https://www.owasp.org/index.php/List_of_useful_HTTP_headers>`_.

Then, in the :ref:`configuration file <config>` (or any other place that you want to enable the tool):

.. code-block:: ini

   [/]
   tools.secureheaders.on = True


If you use :ref:`sessions <basicsession>` you can also enable these settings:

.. code-block:: ini

   [/]
   tools.sessions.on = True
   # increase security on sessions
   tools.sessions.secure = True
   tools.sessions.httponly = True


If you use SSL you can also enable Strict Transport Security:

.. code-block:: python

   # add this to secureheaders():
   # only add Strict-Transport headers if we're actually using SSL; see the ietf spec
   # "An HSTS Host MUST NOT include the STS header field in HTTP responses
   # conveyed over non-secure transport"
   # http://tools.ietf.org/html/draft-ietf-websec-strict-transport-sec-14#section-7.2
   if (cherrypy.server.ssl_certificate != None and cherrypy.server.ssl_private_key != None):
  headers['Strict-Transport-Security'] = 'max-age=31536000'  # one year

Next, you should probably use :ref:`SSL <ssl>`.

Multiple HTTP servers support
#############################

CherryPy starts its own HTTP server whenever you start the
engine. In some cases, you may wish to host your application
on more than a single port. This is easily achieved:

.. code-block:: python

    from cherrypy._cpserver import Server
    server = Server()
    server.socket_port = 8090
    server.subscribe()

You can create as many :class:`server <cherrypy._cpserver.Server>`
server instances as you need, once :ref:`subscribed <busplugins>`,
they will follow the CherryPy engine's life-cycle.

WSGI support
############

CherryPy supports the WSGI interface defined in :pep:`333`
as well as its updates in :pep:`3333`. It means the following:

- You can host a foreign WSGI application with the CherryPy server
- A CherryPy application can be hosted by another WSGI server

Make your CherryPy application a WSGI application
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A WSGI application can be obtained from your application as follows:

.. code-block:: python

    import cherrypy
    wsgiapp = cherrypy.Application(StringGenerator(), '/', config=myconf)

Simply use the `wsgiapp` instance in any WSGI-aware server.

.. _hostwsgiapp:

Host a foreign WSGI application in CherryPy
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Assuming you have a WSGI-aware application, you can host it
in your CherryPy server using the :meth:`cherrypy.tree.graft <cherrypy._cptree.Tree.graft>`
facility.

.. code-block:: python

    def raw_wsgi_app(environ, start_response):
        status = '200 OK'
        response_headers = [('Content-type','text/plain')]
        start_response(status, response_headers)
        return ['Hello world!']

    cherrypy.tree.graft(raw_wsgi_app, '/')

.. important::

   You cannot use tools with a foreign WSGI application.
   However, you can still benefit from the
   :ref:`CherryPy bus <buspattern>`.


No need for the WSGI interface?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The default CherryPy HTTP server supports the WSGI interfaces
defined in :pep:`333` and :pep:`3333`. However, if your application
is a pure CherryPy application, you can switch to a HTTP
server that by-passes the WSGI layer altogether. It will provide
a slight performance increase.

.. code-block:: python

   import cherrypy

   class Root(object):
       @cherrypy.expose
       def index(self):
           return "Hello World!"

   if __name__ == '__main__':
       from cherrypy._cpnative_server import CPHTTPServer
       cherrypy.server.httpserver = CPHTTPServer(cherrypy.server)

       cherrypy.quickstart(Root(), '/')

.. important::

   Using the native server, you will not be able to
   graft a WSGI application as shown in the previous section.
   Doing so will result in a server error at runtime.

WebSocket support
#################

`WebSocket <http://tools.ietf.org/html/rfc6455>`_
is a recent application protocol that came to life
from the HTML5 working-group in response to the needs for
bi-directional communication. Various hacks had been proposed
such as Comet, polling, etc.

WebSocket is a socket that starts its life from a HTTP upgrade request.
Once the upgrade is performed, the underlying socket is
kept opened but not used in a HTTP context any longer.
Instead, both connected endpoints may use the socket
to push data to the other end.

CherryPy itself does not support WebSocket, but the feature
is provided by an external library called
`ws4py <https://github.com/Lawouach/WebSocket-for-Python>`_.

Database support
################

CherryPy does not bundle any database access but its architecture makes it easy
to integrate common database interfaces such as the DB-API specified in
:pep:`249`. Alternatively, you can also use an `ORM
<https://en.wikipedia.org/wiki/Object-relational_mapping>`_ such as `SQLAlchemy
<http://sqlalchemy.readthedocs.org>`_ or `SQLObject
<https://pypi.python.org/pypi/SQLObject/>`_.

You will find `here <https://bitbucket.org/Lawouach/cherrypy-recipes/src/tip/web/database/sql_alchemy/>`_
a recipe on how integrating SQLAlchemy using a mix of
:ref:`plugins <busplugins>` and :ref:`tools <tools>`.

HTML Templating support
#######################

CherryPy does not provide any HTML template but its architecture
makes it easy to integrate one. Popular ones are `Mako <http://www.makotemplates.org>`_
or `Jinja2 <http://jinja.pocoo.org/docs/>`_.

You will find `here <https://bitbucket.org/Lawouach/cherrypy-recipes/src/tip/web/templating/>`_
a recipe on how to integrate them using a mix
:ref:`plugins <busplugins>` and :ref:`tools <tools>`.

Testing your application
########################

Web applications, like any other kind of code, must be tested. CherryPy provides
a :class:`helper class <cherrypy.test.helper.CPWebCase>` to ease writing
functional tests.

Here is a simple example for a basic echo application:

.. code-block:: python

    import cherrypy
    from cherrypy.test import helper

    class SimpleCPTest(helper.CPWebCase):
        def setup_server():
            class Root(object):
                @cherrypy.expose
                def echo(self, message):
                    return message

            cherrypy.tree.mount(Root())
        setup_server = staticmethod(setup_server)

        def test_message_should_be_returned_as_is(self):
            self.getPage("/echo?message=Hello%20world")
            self.assertStatus('200 OK')
            self.assertHeader('Content-Type', 'text/html;charset=utf-8')
            self.assertBody('Hello world')

        def test_non_utf8_message_will_fail(self):
            """
            CherryPy defaults to decode the query-string
            using UTF-8, trying to send a query-string with
            a different encoding will raise a 404 since
            it considers it's a different URL.
            """
            self.getPage("/echo?message=A+bient%F4t",
                         headers=[
                             ('Accept-Charset', 'ISO-8859-1,utf-8'),
                             ('Content-Type', 'text/html;charset=ISO-8859-1')
                         ]
            )
            self.assertStatus('404 Not Found')

As you can see the, test inherits from that helper class. You should
setup your application and mount it as per-usual. Then, define your various
tests and call the helper :meth:`~cherrypy.test.helper.CPWebCase.getPage`
method to perform a request. Simply use the various specialized
assert* methods to validate your workflow and data.

You can then run the test using `py.test <http://pytest.org/latest/>`_ as follows:

.. code-block:: bash

   $ py.test -s test_echo_app.py

The ``-s`` is necessary because the CherryPy class also wraps stdin and stdout.

.. note::

   Although they are written using the typical pattern the
   :mod:`unittest` module supports, they are not bare unit tests.
   Indeed, a whole CherryPy stack is started for you and runs your application.
   If you want to really unit test your CherryPy application, meaning without
   having to start a server, you may want to have a look at
   this `recipe <https://bitbucket.org/Lawouach/cherrypy-recipes/src/tip/testing/unit/serverless/>`_.
