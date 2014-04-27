
Advanced
--------

CherryPy has support for more advanced features that these sections
will describe.

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

If you want to require a password, add one of the ``-aes128``, ``-aes192`` or ``-aes256`` switches to the command above. You should not use any of the DES, 3DES, or SEED algoritms to protect your password, as they are insecure.

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

Run as a daemon
###############

CherryPy allows you to easily decouple the current process from the parent
environment, using the traditional double-fork:

.. code-block:: python

   from cherrypy.process.plugins import Daemonizer
   d = Daemonizer(cherrypy.engine)
   d.subscribe()

.. note::

    This :ref:`Engine Plugin<plugins>` is only available on
    Unix and similar systems which provide fork().

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

Use this :ref:`Engine Plugin<plugins>` to start your
CherryPy site as root (for example, to listen on a privileged port like 80)
and then reduce privileges to something more restricted.

This priority of this plugin's "start" listener is slightly higher than the
priority for ``server.start`` in order to facilitate the most common use:
starting on a low port (which requires root) and then dropping to another user.

.. code-block:: python

   DropPrivileges(cherrypy.engine, uid=1000, gid=1000).subscribe()

PID files
#########

The PIDFile :ref:`Engine Plugin<plugins>` is pretty straightforward: it writes
the process id to a file on start, and deletes the file on exit. You must
provide a 'pidfile' argument, preferably an absolute path:

.. code-block:: python

   PIDFile(cherrypy.engine, '/var/run/myapp.pid').subscribe()

Deal with signals
#################

This :ref:`Engine Plugin<plugins>` is instantiated automatically as
``cherrypy.engine.signal_handler``.
However, it is only *subscribed* automatically by ``cherrypy.quickstart()``.
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

