
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

Response timeouts
#################

CherryPy responses include 3 attributes related to time:

 * ``response.time``: the :func:`time.time` at which the response began
 * ``response.timeout``: the number of seconds to allow responses to run
 * ``response.timed_out``: a boolean indicating whether the response has
   timed out (default False).

The request processing logic inspects the value of ``response.timed_out`` at
various stages; if it is ever True, then :class:`TimeoutError` is raised.
You are free to do the same within your own code.

Rather than calculate the difference by hand, you can call
``response.check_timeout`` to set ``timed_out`` for you.

.. note::
   
   The default response timeout is 300 seconds.

.. _timeoutmonitor:

Timeout Monitor
^^^^^^^^^^^^^^^

In addition, CherryPy includes a ``cherrypy.engine.timeout_monitor`` which
monitors all active requests in a separate thread; periodically, it calls
``check_timeout`` on them all. It is subscribed by default. To turn it off:

.. code-block:: ini

    [global]
    engine.timeout_monitor.on: False

or:

.. code-block:: python

    cherrypy.engine.timeout_monitor.unsubscribe()

You can also change the interval (in seconds) at which the timeout monitor runs:

.. code-block:: ini

    [global]
    engine.timeout_monitor.frequency: 60 * 60

The default is once per minute. The above example changes that to once per hour.

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
When deploying CherryPy on Windows platforms, you should obtain the
`Python for Windows Extensions <http://sourceforge.net/projects/pywin32/>`_;
once you have them installed, CherryPy will handle Ctrl-C and other
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

   def secureheaders():
       headers = cherrypy.response.headers
       headers['X-Frame-Options'] = 'DENY'
       headers['X-XSS-Protection'] = '1; mode=block'
       headers['Content-Security-Policy'] = "default-src='self'"

   # set the priority according to your needs if you are hooking something
   # else on the 'before_finalize' hook point.
   cherrypy.tools.secureheaders = cherrypy.Tool('before_finalize', secureheaders, priority=60)

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

A WSGI application can be obtained from your application as follow:

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

