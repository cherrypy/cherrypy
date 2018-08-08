.. _basics:

Basics
------

The following sections will drive you through the basics of
a CherryPy application, introducing some essential concepts.

.. contents::
   :depth:  4

The one-minute application example
##################################

The most basic application you can write with CherryPy
involves almost all its core concepts.

.. code-block:: python
   :linenos:

   import cherrypy

   class Root(object):
       @cherrypy.expose
       def index(self):
           return "Hello World!"

   if __name__ == '__main__':
      cherrypy.quickstart(Root(), '/')


First and foremost, for most tasks, you will never need more than
a single import statement as demonstrated in line 1.

Before discussing the meat, let's jump to line 9 which shows,
how to host your application with the CherryPy application server
and serve it with its builtin HTTP server at the `'/'` path.
All in one single line. Not bad.

Let's now step back to the actual application. Even though CherryPy
does not mandate it, most of the time your applications
will be written as Python classes. Methods of those classes will
be called by CherryPy to respond to client requests. However,
CherryPy needs to be aware that a method can be used that way, we
say the method needs to be :term:`exposed`. This is precisely
what the :func:`cherrypy.expose()` decorator does in line 4.

Save the snippet in a file named `myapp.py` and run your first
CherryPy application:

.. code-block:: bash

   $ python myapp.py

Then point your browser at http://127.0.0.1:8080. Tada!


.. note::

   CherryPy is a small framework that focuses on one single task:
   take a HTTP request and locate the most appropriate
   Python function or method that match the request's URL.
   Unlike other well-known frameworks, CherryPy does not
   provide a built-in support for database access, HTML
   templating or any other middleware nifty features.

   In a nutshell, once CherryPy has found and called an
   :term:`exposed` method, it is up to you, as a developer, to
   provide the tools to implement your application's logic.

   CherryPy takes the opinion that you, the developer, know best.

.. warning::

   The previous example demonstrated the simplicty of the
   CherryPy interface but, your application will likely
   contain a few other bits and pieces: static service,
   more complex structure, database access, etc.
   This will be developed in the tutorial section.


CherryPy is a minimal framework but not a bare one, it comes
with a few basic tools to cover common usages that you would
expect.

Hosting one or more applications
################################

A web application needs an HTTP server to be accessed to. CherryPy
provides its own, production ready, HTTP server. There are two
ways to host an application with it. The simple one and the almost-as-simple one.

Single application
^^^^^^^^^^^^^^^^^^

The most straightforward way is to use :func:`cherrypy.quickstart`
function. It takes at least one argument, the instance of the
application to host. Two other settings are optionals. First, the
base path at which the application will be accessible from. Second,
a config dictionary or file to configure your application.

.. code-block:: python

   cherrypy.quickstart(Blog())
   cherrypy.quickstart(Blog(), '/blog')
   cherrypy.quickstart(Blog(), '/blog', {'/': {'tools.gzip.on': True}})

The first one means that your application will be available at
http://hostname:port/ whereas the other two will make your blog
application available at http://hostname:port/blog. In addition,
the last one provides specific settings for the application.

.. note::

   Notice in the third case how the settings are still
   relative to the application, not where it is made available at,
   hence the `{'/': ... }` rather than a `{'/blog': ... }`


Multiple applications
^^^^^^^^^^^^^^^^^^^^^

The :func:`cherrypy.quickstart` approach is fine for a single application,
but lacks the capacity to host several applications with the server.
To achieve this, one must use the :meth:`cherrypy.tree.mount <cherrypy._cptree.Tree.mount>`
function as follows:

.. code-block:: python

   cherrypy.tree.mount(Blog(), '/blog', blog_conf)
   cherrypy.tree.mount(Forum(), '/forum', forum_conf)

   cherrypy.engine.start()
   cherrypy.engine.block()

Essentially, :meth:`cherrypy.tree.mount <cherrypy._cptree.Tree.mount>`
takes the same parameters as :func:`cherrypy.quickstart`: an :term:`application`,
a hosting path segment and a configuration. The last two lines
are simply starting application server.

.. important::

   :func:`cherrypy.quickstart` and :meth:`cherrypy.tree.mount <cherrypy._cptree.Tree.mount>`
   are not exclusive. For instance, the previous lines can be written as:

   .. code-block:: python

      cherrypy.tree.mount(Blog(), '/blog', blog_conf)
      cherrypy.quickstart(Forum(), '/forum', forum_conf)

.. note::

   You can also :ref:`host foreign WSGI application <hostwsgiapp>`.


Logging
#######

Logging is an important task in any application. CherryPy will
log all incoming requests as well as protocol errors.

To do so, CherryPy manages two loggers:

- an access one that logs every incoming requests
- an application/error log that traces errors or other application-level messages

Your application may leverage that second logger by calling
:func:`cherrypy.log() <cherrypy._cplogging.LogManager.error>`.

.. code-block:: python

   cherrypy.log("hello there")

You can also log an exception:

.. code-block:: python

   try:
      ...
   except Exception:
      cherrypy.log("kaboom!", traceback=True)

Both logs are writing to files identified by the following keys
in your configuration:

- ``log.access_file`` for incoming requests using the
  `common log format <http://en.wikipedia.org/wiki/Common_Log_Format>`_
- ``log.error_file`` for the other log

.. seealso::

   Refer to the :mod:`cherrypy._cplogging` module for more
   details about CherryPy's logging architecture.

Disable logging
^^^^^^^^^^^^^^^

You may be interested in disabling either logs.

To disable file logging, simply set a en empty string to the
``log.access_file`` or ``log.error_file`` keys in your
:ref:`global configuration <globalsettings>`.

To disable, console logging, set ``log.screen`` to `False`.

.. code-block:: python

    cherrypy.config.update({'log.screen': False,
                            'log.access_file': '',
                            'log.error_file': ''})


Play along with your other loggers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Your application may obviously already use the :mod:`logging`
module to trace application level messages. Below is a simple
example on setting it up.

.. code-block:: python

    import logging
    import logging.config

    import cherrypy

    logger = logging.getLogger()
    db_logger = logging.getLogger('db')

    LOG_CONF = {
        'version': 1,

        'formatters': {
            'void': {
                'format': ''
            },
            'standard': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            },
        },
        'handlers': {
            'default': {
                'level':'INFO',
                'class':'logging.StreamHandler',
                'formatter': 'standard',
                'stream': 'ext://sys.stdout'
            },
            'cherrypy_console': {
                'level':'INFO',
                'class':'logging.StreamHandler',
                'formatter': 'void',
                'stream': 'ext://sys.stdout'
            },
            'cherrypy_access': {
                'level':'INFO',
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'void',
                'filename': 'access.log',
                'maxBytes': 10485760,
                'backupCount': 20,
                'encoding': 'utf8'
            },
            'cherrypy_error': {
                'level':'INFO',
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'void',
                'filename': 'errors.log',
                'maxBytes': 10485760,
                'backupCount': 20,
                'encoding': 'utf8'
            },
        },
        'loggers': {
            '': {
                'handlers': ['default'],
                'level': 'INFO'
            },
            'db': {
                'handlers': ['default'],
                'level': 'INFO' ,
                'propagate': False
            },
            'cherrypy.access': {
                'handlers': ['cherrypy_access'],
                'level': 'INFO',
                'propagate': False
            },
            'cherrypy.error': {
                'handlers': ['cherrypy_console', 'cherrypy_error'],
                'level': 'INFO',
                'propagate': False
            },
        }
    }

    class Root(object):
        @cherrypy.expose
        def index(self):

            logger.info("boom")
            db_logger.info("bam")
            cherrypy.log("bang")

            return "hello world"

    if __name__ == '__main__':
        cherrypy.config.update({'log.screen': False,
                                'log.access_file': '',
                                'log.error_file': ''})
    cherrypy.engine.unsubscribe('graceful', cherrypy.log.reopen_files)
        logging.config.dictConfig(LOG_CONF)
        cherrypy.quickstart(Root())


In this snippet, we create a `configuration dictionary <https://docs.python.org/2/library/logging.config.html#logging.config.dictConfig>`_
that we pass on to the ``logging`` module to configure
our loggers:

 * the default root logger is associated to a single stream handler
 * a logger for the db backend with also a single stream handler

In addition, we re-configure the CherryPy loggers:

 * the top-level ``cherrypy.access`` logger to log requests into a file
 * the ``cherrypy.error`` logger to log everything else into a file
   and to the console

We also prevent CherryPy from trying to open its log files when
the autoreloader kicks in. This is not strictly required since we do not
even let CherryPy open them in the first place. But, this avoids
wasting time on something useless.


.. _config:

Configuring
###########

CherryPy comes with a fine-grained configuration mechanism and
settings can be set at various levels.

.. seealso::

   Once you have the reviewed the basics, please refer
   to the :ref:`in-depth discussion <configindepth>`
   around configuration.

.. _globalsettings:

Global server configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^

To configure the HTTP and application servers,
use the :meth:`cherrypy.config.update() <cherrypy._cpconfig.Config.update>`
method.

.. code-block:: python

   cherrypy.config.update({'server.socket_port': 9090})

The :mod:`cherrypy.config <cherrypy._cpconfig>` object is a dictionary and the
update method merges the passed dictionary into it.

You can also pass a file instead (assuming a `server.conf`
file):

.. code-block:: ini

   [global]
   server.socket_port: 9090

.. code-block:: python

   cherrypy.config.update("server.conf")

.. warning::

   :meth:`cherrypy.config.update() <cherrypy._cpconfig.Config.update>`
   is not meant to be used to configure the application.
   It is a common mistake. It is used to configure the server and engine.

.. _perappconf:

Per-application configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To configure your application, pass in a dictionary or a file
when you associate your application to the server.

.. code-block:: python

   cherrypy.quickstart(myapp, '/', {'/': {'tools.gzip.on': True}})

or via a file (called `app.conf` for instance):

.. code-block:: ini

   [/]
   tools.gzip.on: True

.. code-block:: python

   cherrypy.quickstart(myapp, '/', "app.conf")

Although, you can define most of your configuration in a global
fashion, it is sometimes convenient to define them
where they are applied in the code.

.. code-block:: python

   class Root(object):
       @cherrypy.expose
       @cherrypy.tools.gzip()
       def index(self):
           return "hello world!"

A variant notation to the above:

.. code-block:: python

   class Root(object):
       @cherrypy.expose
       def index(self):
           return "hello world!"
       index._cp_config = {'tools.gzip.on': True}

Both methods have the same effect so pick the one
that suits your style best.

Additional application settings
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can add settings that are not specific to a request URL
and retrieve them from your page handler as follows:

.. code-block:: ini

   [/]
   tools.gzip.on: True

   [googleapi]
   key = "..."
   appid = "..."

.. code-block:: python

   class Root(object):
       @cherrypy.expose
       def index(self):
           google_appid = cherrypy.request.app.config['googleapi']['appid']
           return "hello world!"

   cherrypy.quickstart(Root(), '/', "app.conf")


Cookies
#######

CherryPy uses the :mod:`Cookie` module from python and in particular the
:class:`Cookie.SimpleCookie` object type to handle cookies.

- To send a cookie to a browser, set ``cherrypy.response.cookie[key] = value``.
- To retrieve a cookie sent by a browser, use ``cherrypy.request.cookie[key]``.
- To delete a cookie (on the client side), you must *send* the cookie with its
  expiration time set to `0`:

.. code-block:: python

    cherrypy.response.cookie[key] = value
    cherrypy.response.cookie[key]['expires'] = 0

It's important to understand that the request cookies are **not** automatically
copied to the response cookies. Clients will send the same cookies on every
request, and therefore ``cherrypy.request.cookie`` should be populated each
time. But the server doesn't need to send the same cookies with every response;
therefore, ``cherrypy.response.cookie`` will usually be empty. When you wish
to “delete” (expire) a cookie, therefore, you must set
``cherrypy.response.cookie[key] = value`` first, and then set its ``expires``
attribute to 0.

Extended example:

.. code-block:: python

    import cherrypy

    class MyCookieApp(object):
        @cherrypy.expose
        def set(self):
            cookie = cherrypy.response.cookie
            cookie['cookieName'] = 'cookieValue'
            cookie['cookieName']['path'] = '/'
            cookie['cookieName']['max-age'] = 3600
            cookie['cookieName']['version'] = 1
            return "<html><body>Hello, I just sent you a cookie</body></html>"

        @cherrypy.expose
        def read(self):
            cookie = cherrypy.request.cookie
            res = """<html><body>Hi, you sent me %s cookies.<br />
                    Here is a list of cookie names/values:<br />""" % len(cookie)
            for name in cookie.keys():
                res += "name: %s, value: %s<br>" % (name, cookie[name].value)
            return res + "</body></html>"

    if __name__ == '__main__':
        cherrypy.quickstart(MyCookieApp(), '/cookie')


.. _basicsession:

Using sessions
##############

Sessions are one of the most common mechanism used by developers to
identify users and synchronize their activity. By default, CherryPy
does not activate sessions because it is not a mandatory feature
to have, to enable it simply add the following settings in your
configuration:

.. code-block:: ini

   [/]
   tools.sessions.on: True

.. code-block:: python

   cherrypy.quickstart(myapp, '/', "app.conf")

Sessions are, by default, stored in RAM so, if you restart your server
all of your current sessions will be lost. You can store them in memcached
or on the filesystem instead.

Using sessions in your applications is done as follows:

.. code-block:: python

   import cherrypy

   @cherrypy.expose
   def index(self):
       if 'count' not in cherrypy.session:
          cherrypy.session['count'] = 0
       cherrypy.session['count'] += 1

In this snippet, everytime the the index page handler is called,
the current user's session has its `'count'` key incremented by `1`.

CherryPy knows which session to use by inspecting the cookie
sent alongside the request. This cookie contains the session
identifier used by CherryPy to load the user's session from
the storage.

.. seealso::

   Refer to the :mod:`cherrypy.lib.sessions` module for more
   details about the session interface and implementation.
   Notably you will learn about sessions expiration.

Filesystem backend
^^^^^^^^^^^^^^^^^^

Using a filesystem is a simple to not lose your sessions
between reboots. Each session is saved in its own file within
the given directory.

.. code-block:: ini

   [/]
   tools.sessions.on: True
   tools.sessions.storage_class = cherrypy.lib.sessions.FileSession
   tools.sessions.storage_path = "/some/directory"

Memcached backend
^^^^^^^^^^^^^^^^^

`Memcached <http://memcached.org/>`_ is a popular key-store on top of your RAM,
it is distributed and a good choice if you want to
share sessions outside of the process running CherryPy.

Requires that the Python
`memcached <https://pypi.org/project/memcached>`_
package is installed, which may be indicated by installing
``cherrypy[memcached_session]``.

.. code-block:: ini

   [/]
   tools.sessions.on: True
   tools.sessions.storage_class = cherrypy.lib.sessions.MemcachedSession

.. _staticontent:

Other backends
^^^^^^^^^^^^^^

Any other library may implement a session backend. Simply subclass
``cherrypy.lib.sessions.Session`` and indicate that subclass as
``tools.sessions.storage_class``.

Static content serving
######################

CherryPy can serve your static content such as images, javascript and
CSS resources, etc.

.. note::

   CherryPy uses the :mod:`mimetypes` module to determine the
   best content-type to serve a particular resource. If the choice
   is not valid, you can simply set more media-types as follows:

   .. code-block:: python

      import mimetypes
      mimetypes.types_map['.csv'] = 'text/csv'


Serving a single file
^^^^^^^^^^^^^^^^^^^^^

You can serve a single file as follows:

.. code-block:: ini

   [/style.css]
   tools.staticfile.on = True
   tools.staticfile.filename = "/home/site/style.css"

CherryPy will automatically respond to URLs such as
`http://hostname/style.css`.

Serving a whole directory
^^^^^^^^^^^^^^^^^^^^^^^^^

Serving a whole directory is similar to a single file:

.. code-block:: ini

   [/static]
   tools.staticdir.on = True
   tools.staticdir.dir = "/home/site/static"

Assuming you have a file at `static/js/my.js`,
CherryPy will automatically respond to URLs such as
`http://hostname/static/js/my.js`.


.. note::

   CherryPy always requires the absolute path to the files or directories
   it will serve. If you have several static sections to configure
   but located in the same root directory, you can use the following
   shortcut:


   .. code-block:: ini

      [/]
      tools.staticdir.root = "/home/site"

      [/static]
      tools.staticdir.on = True
      tools.staticdir.dir = "static"

Specifying an index file
^^^^^^^^^^^^^^^^^^^^^^^^^

By default, CherryPy will respond to the root of a static
directory with an 404 error indicating the path '/' was not found.
To specify an index file, you can use the following:

.. code-block:: ini

   [/static]
   tools.staticdir.on = True
   tools.staticdir.dir = "/home/site/static"
   tools.staticdir.index = "index.html"

Assuming you have a file at `static/index.html`,
CherryPy will automatically respond to URLs such as
`http://hostname/static/` by returning its contents.


Allow files downloading
^^^^^^^^^^^^^^^^^^^^^^^

Using ``"application/x-download"`` response content-type,
you can tell a browser that a resource should be downloaded
onto the user's machine rather than displayed.

You could for instance write a page handler as follows:

.. code-block:: python

    from cherrypy.lib.static import serve_file

    @cherrypy.expose
    def download(self, filepath):
        return serve_file(filepath, "application/x-download", "attachment")

Assuming the filepath is a valid path on your machine, the
response would be considered as a downloadable content by
the browser.

.. warning::

   The above page handler is a security risk on its own since any file
   of the server could be accessed (if the user running the
   server had permissions on them).


Dealing with JSON
#################

CherryPy has built-in support for JSON encoding and decoding
of the request and/or response.

Decoding request
^^^^^^^^^^^^^^^^

To automatically decode the content of a request using JSON:

.. code-block:: python

   class Root(object):
       @cherrypy.expose
       @cherrypy.tools.json_in()
       def index(self):
           data = cherrypy.request.json

The `json` attribute attached to the request contains
the decoded content.

Encoding response
^^^^^^^^^^^^^^^^^

To automatically encode the content of a response using JSON:

.. code-block:: python

   class Root(object):
       @cherrypy.expose
       @cherrypy.tools.json_out()
       def index(self):
           return {'key': 'value'}

CherryPy will encode any content returned by your page handler
using JSON. Not all type of objects may natively be
encoded.

Authentication
##############

CherryPy provides support for two very simple HTTP-based
authentication mechanisms, described in :rfc:`7616` and :rfc:`7617`
(which obsoletes :rfc:`2617`): Basic and Digest. They are most
commonly known to trigger a browser's popup asking users their name
and password.

Basic
^^^^^

Basic authentication is the simplest form of authentication however
it is not a secure one as the user's credentials are embedded into
the request. We advise against using it unless you are running on
SSL or within a closed network.

.. code-block:: python

   from cherrypy.lib import auth_basic

   USERS = {'jon': 'secret'}

   def validate_password(realm, username, password):
       if username in USERS and USERS[username] == password:
          return True
       return False

   conf = {
      '/protected/area': {
          'tools.auth_basic.on': True,
          'tools.auth_basic.realm': 'localhost',
          'tools.auth_basic.checkpassword': validate_password,
          'tools.auth_basic.accept_charset': 'UTF-8',
       }
   }

   cherrypy.quickstart(myapp, '/', conf)

Simply put, you have to provide a function that will
be called by CherryPy passing the username and password
decoded from the request.

The function can read its data from any source it has to: a file,
a database, memory, etc.


Digest
^^^^^^

Digest authentication differs by the fact the credentials
are not carried on by the request so it's a little more secure
than basic.

CherryPy's digest support has a similar interface to the
basic one explained above.

.. code-block:: python

   from cherrypy.lib import auth_digest

   USERS = {'jon': 'secret'}

   conf = {
      '/protected/area': {
           'tools.auth_digest.on': True,
           'tools.auth_digest.realm': 'localhost',
           'tools.auth_digest.get_ha1': auth_digest.get_ha1_dict_plain(USERS),
           'tools.auth_digest.key': 'a565c27146791cfb',
           'tools.auth_digest.accept_charset': 'UTF-8',
      }
   }

   cherrypy.quickstart(myapp, '/', conf)

SO_PEERCRED
^^^^^^^^^^^

There's also a low-level authentication for UNIX file and abstract
sockets. This is how you enable it:

.. code-block:: ini

   [global]
   server.peercreds: True
   server.peercreds_resolve: True
   server.socket_file: /var/run/cherrypy.sock

``server.peercreds`` enables looking up the connected process ID,
user ID and group ID. They'll be accessible as WSGI environment
variables::

    * ``X_REMOTE_PID``

    * ``X_REMOTE_UID``

    * ``X_REMOTE_GID``

``server.peercreds_resolve`` resolves that into user name and group
name. They'll be accessible as WSGI environment variables::

    * ``X_REMOTE_USER`` and ``REMOTE_USER``

    * ``X_REMOTE_GROUP``

Favicon
#######

CherryPy serves its own sweet red cherrypy as the default
`favicon <http://en.wikipedia.org/wiki/Favicon>`_ using the static file
tool. You can serve your own favicon as follows:

.. code-block:: python

    import cherrypy

    class HelloWorld(object):
       @cherrypy.expose
       def index(self):
           return "Hello World!"

    if __name__ == '__main__':
        cherrypy.quickstart(HelloWorld(), '/',
            {
                '/favicon.ico':
                {
                    'tools.staticfile.on': True,
                    'tools.staticfile.filename': '/path/to/myfavicon.ico'
                }
            }
        )

Please refer to the :ref:`static serving <staticontent>` section
for more details.

You can also use a file to configure it:

.. code-block:: ini

    [/favicon.ico]
    tools.staticfile.on: True
    tools.staticfile.filename: "/path/to/myfavicon.ico"


.. code-block:: python

    import cherrypy

    class HelloWorld(object):
       @cherrypy.expose
       def index(self):
           return "Hello World!"

    if __name__ == '__main__':
        cherrypy.quickstart(HelloWorld(), '/', "app.conf")
