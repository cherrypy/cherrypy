
Advanced
--------

CherryPy has support for more advanced features that these sections
will describe.

.. contents::
   :depth:  4

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

