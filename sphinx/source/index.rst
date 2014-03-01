
CherryPy - A Minimalist Python Web Framework
============================================


CherryPy is a pythonic, object-oriented web framework.

CherryPy allows developers to build web applications in much the same way they would build any other object-oriented Python program. This results in smaller source code developed in less time.

CherryPy is now more than seven years old and it is has proven to be very fast and stable. It is being used in production by many sites, from the simplest to the most demanding.

A CherryPy application typically looks like this:

.. code-block:: python

   import cherrypy
   
   class HelloWorld(object):
       @cherrypy.expose
       def index(self):
           return "Hello World!"

   cherrypy.quickstart(HelloWorld())


.. contents::
   :depth: 4

Foreword
========

Why CherryPy?
-------------

CherryPy is among the oldest web framework available for Python, yet many people aren't aware of its existence. 
One of the reason for this is that CherryPy is not a complete stack with built-in support for a multi-tier architecture.
It doesn't provide frontend utilities nor will it tell you how to speak with your storage. Instead, CherryPy's take
is to let the developer make those decisions. This is a contrasting position compared to other well-known frameworks. 

CherryPy has a clean interface and does its best to stay out of your way whilst providing
a reliable scaffolding for you to build from.

Typical use-cases for CherryPy go from regular web application with user frontends 
(think blogging, CMS, portals, ecommerce) to web-services only.



Installation
============

CherryPy is a pure Python library. This has various consequences:

 - It can run anywhere Python runs
 - It does not require a C compiler
 - It can run on various implementations of the Python language: `CPython <http://python.org/>`_, 
   `IronPython <http://ironpython.net/>`_, `Jython <http://www.jython.org/>`_ and `PyPy <http://pypy.org/>`_

Requirements
------------

CherryPy does not have any mandatory requirements. However certain features it comes with
will require you install certain packages.

- `routes <http://routes.readthedocs.org/en/latest/>`_ for declarative URL mapping dispatcher
- `psycopg2 <http://pythonhosted.org//psycopg2/>`_ for PostgreSQL backend session
- `pywin32 <http://sourceforge.net/projects/pywin32/>`_ for Windows services
- `python-memcached <https://github.com/linsomniac/python-memcached>`_ for memcached backend session
- `simplejson <https://github.com/simplejson/simplejson>`_ for a better JSON support

Supported python version
------------------------

CherryPy supports Python 2.3 through to 3.4.


Installing
----------

CherryPy can be easily installed via common Python package managers such as setuptools or pip.

.. code-block:: bash

   $ easy_install cherrypy


.. code-block:: bash

   $ pip install cherrypy

You may also get the latest CherryPy version by grabbing the source code from BitBucket:

.. code-block:: bash

   $ hg clone https://bitbucket.org/cherrypy/cherrypy
   $ cd cherrypy
   $ python setup.py install

Run it
------

CherryPy comes with a set of simple tutorials that can be executed
once you have deployed the package.

.. code-block:: bash

   $ python -m cherrypy.tutorial.tut01_helloworld

Point your browser at http://127.0.0.1:8080 and enjoy the magic.

Once started the above command shows the following logs:

.. code-block:: bash

   [15/Feb/2014:21:51:22] ENGINE Listening for SIGHUP.
   [15/Feb/2014:21:51:22] ENGINE Listening for SIGTERM.
   [15/Feb/2014:21:51:22] ENGINE Listening for SIGUSR1.
   [15/Feb/2014:21:51:22] ENGINE Bus STARTING
   [15/Feb/2014:21:51:22] ENGINE Started monitor thread 'Autoreloader'.
   [15/Feb/2014:21:51:22] ENGINE Started monitor thread '_TimeoutMonitor'.
   [15/Feb/2014:21:51:22] ENGINE Serving on http://127.0.0.1:8080
   [15/Feb/2014:21:51:23] ENGINE Bus STARTED

We will explain what all those lines mean later on, but suffice
to know that once you see the last two lines, your server
is listening and ready to receive requests.


Glossary
========

.. glossary:: 

   exposed
      A Python function or method which has an attribute called `exposed`
      set to `True`. This attribute can be set directly or via the 
      :func:`cherrypy.expose()` decorator.

      .. code-block:: python
		      
         @cherrypy.expose
	 def method(...):
	     ...

      is equivalent to:

      .. code-block:: python
		      
	 def method(...):
	     ...
         method.exposed = True
         
   page handler
      Name commonly given to an exposed method

   controller
      Name commonly given to a class owning at least one exposed method

Get Started
===========

The following sections will drive you through the basics of
a CherryPy application, introducing some essential concepts.

The one-minute application example
----------------------------------

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


Common tasks
------------

CherryPy is a minimal framework but not a bare one, it comes
with a few basic tools to cover common usages that you would
expect.

Logging
^^^^^^^

Logging is an important task in any application. CherryPy will
log all incoming requests as well as protocol errors.

To do so, CherryPy manages two loggers:

- an access one that logs every incoming requests 
- an application/error log that traces errors or other application-level messages

Your application may leverage that second logger by calling
:func:`cherrypy.log()`. 

.. code-block:: python

   cherrypy.log("hello there")

You can also log an exception:

.. code-block:: python

   try:
      ...
   except:
      cherrypy.log("kaboom!", traceback=True)

Both logs are writing to files identified by the following keys
in your configuration:

- `log.access_file` for incoming requests using the 
  `common log format <http://en.wikipedia.org/wiki/Common_Log_Format>`_
- `log.error_file` for the other log

Disable logging
###############

You may be interested in disable either log. To do so, simply
set a en empty string to the `log.access_file` or `log.error_file`
parameters.

Play along with your other logs
###############################

Your application may aobviously already use the :mod:`logging`
module to trace application level messages. CherryPy will not
interfere with them as long as your loggers are explicitely
named. Indeed, CherryPy attaches itself to the default
logger and if your other loggers do the same, you will get
strange logs. This would work nicely:

.. code-block:: python
		
    import logging
    logger = logging.getLogger('myapp.mypackage')
    logger.setLevel(logging.INFO)
    stream = logging.StreamHandler()
    stream.setLevel(logging.INFO)
    logger.addHandler(stream)


Configuring
^^^^^^^^^^^

CherryPy comes with a fine-grained configuration mechanism and 
settings can be set at various levels.

Global server settings
######################

To configure the HTTP server, use the :func:`cherrypy.config.update()` method.

.. code-block:: python

   cherrypy.config.update({'server.socket_port': 9090})

The `cherrypy.config` object is a dictionary and the 
update method merge the passed dictionary into it.

You can also pass a file instead (assuming a `server.conf`
file):

.. code-block:: ini

   [global]
   server.socket_port: 9090

.. code-block:: python

   cherrypy.config.update("server.conf")

.. _perappconf:

Global application settings
###########################

To configure the application settings, pass a dictionary
or a file when you associate your application
to the server.

.. code-block:: python

   cherrypy.quickstart(myapp, '/', {'/': {'tools.gzip.on': True}})

or via a file (called `app.conf` for instance):

.. code-block:: ini

   [/]
   tools.gzip.on: True

.. code-block:: python

   cherrypy.quickstart(myapp, '/', "app.conf")
 

Local application settings
##########################

Although, you can define most of your settings in a global
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

.. _basicsession:

Using sessions
^^^^^^^^^^^^^^

Sessions is one of the most common mechanism used by developers to 
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

Using sessions in your applications is done as follow:

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

Filesystem backend
##################

Using a filesystem is a simple not to lose your sessions
between reboots. Each session is saved in its own file within
the given directory. 

.. code-block:: ini

   [/]
   tools.sessions.on: True
   tools.sessions.storage_type = "file"
   tools.sessions.storage_path = "/some/directorys"

Memcached backend
#################

`Memcached <http://memcached.org/>`_ is a popular key-store on top of your RAM, 
it is distributed and a good choice if you want to
share sessions outside of the process running CherryPy.

.. code-block:: ini

   [/]
   tools.sessions.on: True
   tools.sessions.storage_type = "memcached"

Static serving
^^^^^^^^^^^^^^

CherryPy can serve your static content such as images, javascript and 
CSS resources, etc. 

Serving a single file
#####################

You can serve a single file as follow:

.. code-block:: ini

   [/style.css]
   tools.staticfile.on = True
   tools.staticfile.filename = "/home/site/style.css"

CherryPy will automatically respond to URLs such as 
`http://hostname/style.css`.

Serving a whole directory
#########################

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
   it will serve. If you have several static section to configure
   but located in the same root directory, you can use the following 
   shortcut:

   
   .. code-block:: ini

      [/]
      tools.staticdir.root = "/home/site"

      [/static]
      tools.staticdir.on = True
      tools.staticdir.dir = "static"

Dealing with JSON
^^^^^^^^^^^^^^^^^

CherryPy has a built-in support for JSON encoding and decoding
of the request and/or response.

Decoding request
################

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
#################

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
^^^^^^^^^^^^^^

CherryPy provides support for two very simple authentications mechanism,
both described in :rfc:`2617`: Basic and Digest. They are most commonly
known to trigger a browser's popup asking users their name
and password.

Basic
#####

Basic authentication is the simplest form of authentication however
it is not a secure one as the user's credentials are embedded into
the request. We advise against using it unless you are running on
SSL or within a closed network.

.. code-block:: python

   from cherrypy.lib import auth_basic

   USERS = {'jon': 'secret'}

   def validate_password(username, password):
       if username in USERS and USERS[username] == password:
          return True
       return False

   conf = {
      '/protected/area': {
          'tools.auth_basic.on': True,
          'tools.auth_basic.realm': 'localhost',
          'tools.auth_basic.checkpassword': validate_password
       } 
   }

   cherrypy.quickstart(myapp, '/', conf)

Simply put, you have to provide a function that will
be called by CherryPy passing the username and password 
decoded from the request.

The function can read its data from any source it has to: a file,
a database, memory, etc.


Digest
######

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
           'tools.auth_digest.key': 'a565c27146791cfb'
      }
   }

   cherrypy.quickstart(myapp, '/', conf)

Tutorials
=========

This tutorial will walk you through basic but complete CherryPy applications
that will show you common concepts as well as slightly more adavanced ones.

Tutorial 1: A basic web application
-----------------------------------

The following example demonstrates the most basic application
you could write with CherryPy. It starts a server and hosts
an application that will be served at request reaching
http://127.0.0.1:8080/

.. code-block:: python
   :linenos:

   import cherrypy

   class HelloWorld(object):
       @cherrypy.expose
       def index(self):
	   return "Hello world!"

   if __name__ == '__main__':
      cherrypy.quickstart(HelloWorld())

Store this code snippet into a file named `tut01.py` and
execute it as follow:

.. code-block:: bash

   $ python tut01.py

This will display something along the following:

.. code-block:: text
   :linenos:

   [24/Feb/2014:21:01:46] ENGINE Listening for SIGHUP.
   [24/Feb/2014:21:01:46] ENGINE Listening for SIGTERM.
   [24/Feb/2014:21:01:46] ENGINE Listening for SIGUSR1.
   [24/Feb/2014:21:01:46] ENGINE Bus STARTING
   CherryPy Checker:
   The Application mounted at '' has an empty config.
   
   [24/Feb/2014:21:01:46] ENGINE Started monitor thread 'Autoreloader'.
   [24/Feb/2014:21:01:46] ENGINE Started monitor thread '_TimeoutMonitor'.
   [24/Feb/2014:21:01:46] ENGINE Serving on http://127.0.0.1:8080
   [24/Feb/2014:21:01:46] ENGINE Bus STARTED

This tells you several things. The first three lines indicate
the server will handle :mod:`signal` for you. The next line tells you 
the current state of the server, as that
point it is in `STARTING` stage. Then, you are notified your
application has no specific configuration set to it.
Next, the server starts a couple of internal utilities that
we will explain later. Finally, the server indicates it is now
ready to accept incoming communications as it listens on
the address `127.0.0.1:8080`. In other words, at that stage your
application is ready to be used.

Before moving on, let's discuss the message
regarding the lack of configuration. By default, CherryPy has
a feature which will review the syntax correctness of settings
you could provide to configure the application. When none are
provided, a warning message is thus displayed in the logs. That
log is harmless and will not prevent CherryPy from working. You
can refer to :ref:`the documentation above <perappconf>` to
understand how to set the configuration.

Tutorial 2: Different URLs lead to different functions
------------------------------------------------------

Your applications will obviously handle more than a single URL. 
Let's imagine you have an application that generates a random 
string each time it is called:

.. code-block:: python
   :linenos:

   import random
   import string
   
   import cherrypy

   class StringGenerator(object):
       @cherrypy.expose
       def index(self):
	   return "Hello world!"

       @cherrypy.expose
       def generate(self):
           return ''.join(random.sample(string.hexdigits, 8))
    
   if __name__ == '__main__':
       cherrypy.quickstart(StringGenerator())

Save this into a file named `tut02.py` and run it as follow:

.. code-block:: bash

   $ python tut02.py

Go now to http://localhost:8080/generate and your browser
will display a random string. 

Let's take a minute to decompose what's happening here. This is the
URL that you have typed into your browser: http://localhost:8080/generate

This URL contains various parts:

- `http://` which roughly indicates it's a URL using the HTTP protocol (see :rfc:`2616`).
- `localhost:8080` is the server's address. It's made of a hostname and a port.
- `/generate` which is the path segment of the URL. This is what ultimately uses to
  try and locate an appropriate exposed function or method to respond.

Here CherryPy uses the `index()` method to handle `/` and the
`generate()` method to handle `/generate`

.. _tut03:

Tutorial 3: My URLs have parameters
-----------------------------------

In the previous tutorial, we have seen how to create an application
that could generate a random string. Let's not assume you wish
to indicate the length of that string dynamically.

.. code-block:: python
   :linenos:

   import random
   import string
   
   import cherrypy

   class StringGenerator(object):
       @cherrypy.expose
       def index(self):
	   return "Hello world!"

       @cherrypy.expose
       def generate(self, length=8):
           return ''.join(random.sample(string.hexdigits, int(length)))
    
   if __name__ == '__main__':
       cherrypy.quickstart(StringGenerator())

Save this into a file named `tut03.py` and run it as follow:

.. code-block:: bash

   $ python tut03.py

Go now to http://localhost:8080/generate?length=16 and your browser
will display a generated string of length 16. Notice how
we benefit from Python's default arguments' values to support 
URLs such as http://localhost:8080/password still.

In a URL such as this one, the section after `?` is called a 
query-string. Traditionally, the query-string is used to 
contextualize the URL by passing a set of (key, value) pairs. The
format for those pairs is `key=value`. Each pair being
separated by a `&` character.

Notice how we have to convert the given `length` value to
and integer. Indeed, values are sent out from the client
to our server as strings. 

Much like CherryPy maps URL path segments to exposed functions,
query-string keys are mapped to those exposed function parameters.

.. _tut04:

Tutorial 4: Submit this form
----------------------------

CherryPy is a web framework upon which you build web applications.
The most traditionnal shape taken by applications is through
an HTML user-interface speaking to your CherryPy server.

Let's see how to handle HTML forms via the following
example.

.. code-block:: python
   :linenos:

   import random
   import string
   
   import cherrypy

   class StringGenerator(object):
       @cherrypy.expose
       def index(self):
	   return """<html>
             <head></head>
	     <body>
	       <form method="get" action="generate">
	         <input type="text" value="8" name="length" />
                 <button type="submit">Give it now!</button>
	       </form>
	     </body>
	   </html>"""

       @cherrypy.expose
       def generate(self, length=8):
           return ''.join(random.sample(string.hexdigits, int(length)))
    
   if __name__ == '__main__':
       cherrypy.quickstart(StringGenerator())

Save this into a file named `tut04.py` and run it as follow:

.. code-block:: bash

   $ python tut04.py

Go now to http://localhost:8080/ and your browser and this will
display a simple input field to indicate the length of the string
you want to generate.

Notice that in this example, the form uses the `GET` method and 
when you pressed the `Give it now!` button, the form is sent using the
same URL as in the :ref:`previous <tut03>` tutorial. HTML forms also support the 
`POST` method, in that case the query-string is not appended to the
URL but it sent as the body of the client's request to the server.
However, this would not change your application's exposed method because
CherryPy handles both the same way and uses the exposed's handler
parameters to deal with the query-string (key, value) pairs.

.. _tut05:

Tutorial 5: Track my end-user's activity
----------------------------------------

It's not uncommon that an application needs to follow the
user's activity for a while. The usual mechanism is to use
a `session identifier <http://en.wikipedia.org/wiki/Session_(computer_science)#HTTP_session_token>`_
that is carried during the conversation between the user and 
your application. 

.. code-block:: python
   :linenos:

    import random
    import string

    import cherrypy

    class StringGenerator(object):
       @cherrypy.expose
       def index(self):
           return """<html>
             <head></head>
         <body>
           <form method="get" action="generate">
             <input type="text" value="8" name="length" />
                 <button type="submit">Give it now!</button>
           </form>
         </body>
       </html>"""

       @cherrypy.expose
       def generate(self, length=8):
           some_string = ''.join(random.sample(string.hexdigits, int(length)))
           cherrypy.session['mystring'] = some_string
           return some_string

       @cherrypy.expose
       def display(self):
           return cherrypy.session['mystring']

    if __name__ == '__main__':
        conf = {
            '/': {
                'tools.sessions.on': True
            }
        }
        cherrypy.quickstart(StringGenerator(), '/', conf)

Save this into a file named `tut05.py` and run it as follow:

.. code-block:: bash

   $ python tut05.py

In this example, we generate the string as in the 
:ref:`previous <tut04>` tutorial but also store it in the current
session. If you go to http://localhostt:8080/, generate a
random string, then go to http://localhostt:8080/display, you
will see the string you just generated. 

The lines 30-34 show you how to enable the session support
in your CherryPy application. By default, CherryPy will save
sessions in the process's memory. It supports more persistent
:ref:`backends <basicsession>` as well.

Tutorial 6: What about my javascripts, CSS and images?
------------------------------------------------------

Web application are usually also made of static content such
as javascript, CSS files or images. CherryPy provides support
to serve static content to end-users.

Let's assume, you want to associate a stylesheet with your
application to display a blue background color (why not?).

First, save the following stylesheet into a file named `style.css`
and stored into a local directory `public/css`.

.. code-block:: css
   :linenos:

      body { 
        background-color: blue;
      }

Now let's update the HTML code so that we link to the stylesheet
using the http://localhost:8080/static/css/style.css URL.

.. code-block:: python
   :linenos:

    import os, os.path
    import random
    import string

    import cherrypy

    class StringGenerator(object):
       @cherrypy.expose
       def index(self):
           return """<html>
             <head>
               <link href="/static/css/style.css" rel="stylesheet">
             </head>
         <body>
           <form method="get" action="generate">
             <input type="text" value="8" name="length" />
                 <button type="submit">Give it now!</button>
           </form>
         </body>
       </html>"""

       @cherrypy.expose
       def generate(self, length=8):
           some_string = ''.join(random.sample(string.hexdigits, int(length)))
           cherrypy.session['mystring'] = some_string
           return some_string

       @cherrypy.expose
       def display(self):
           return cherrypy.session['mystring']

    if __name__ == '__main__':
        conf = {
            '/': {
                'tools.sessions.on': True,
		'tools.staticdir.root': os.path.abspath(os.getcwd())
            },
            '/static': {
                'tools.staticdir.on': True,
		'tools.staticdir.dir': './public'
            }
        }
        cherrypy.quickstart(StringGenerator(), '/', conf)

Save this into a file named `tut06.py` and run it as follow:

.. code-block:: bash

   $ python tut06.py

Going to http://localhost:8080/, you should be greeted by a flashy blue color.

CherryPy provides support to serve a single file or a complete
directory structure. Most of the time, this is what you'll end
up doing so this is what the code above demonstrates. First, we
indicate the `root` directory of all of our static content. This
must be an absolute path for security reason. CherryPy will
complain if you provide only non-absolute paths when looking for a
match to your URLs.

Then we indicate that all URLs which path segment starts with `/static`
will be served as static content. We map that URL to the `public`
directory, a direct child of the `root` directory. The entire
sub-tree of the `public` directory will be served as static content.
CherryPy will map URLs to path within that directory. This is why
`/static/css/style.css` is found in `public/css/style.css`.

Tutorial 7: Give us a REST
--------------------------

It's not unusual nowadays that web applications expose some sort
of datamodel or computation functions. Without going into
its details, one strategy is to follow the `REST principles
edicted by Roy T. Fielding in his thesis 
<https://www.ics.uci.edu/~fielding/pubs/dissertation/rest_arch_style.htm>`_.

Roughly speaking, it assumes that you can identify a resource
and that you can address that resource through that identifier.

"What for?" you may ask. Well, mostly, these principles are there
to ensure that you decouple, as best as you can, the entities 
your application expose from the way they are manipulated or
consumed. To embrace this point of view, developers will
usually design a web API that expose pairs of `(URL, HTTP method)`.

.. note::

   You will often hear REST and web API together. The former is
   one strategy to provide the latter. This tutorial will not go
   deeper in that whole web API concept as it's a much more
   engaging subject, but you ought to read more about it online.


Lets go through a small example of a very basic web API
midly following REST principles.

.. code-block:: python
   :linenos:

    import random
    import string

    import cherrypy

    class StringGeneratorWebService(object):
        exposed = True

        @cherrypy.tools.accept(media='text/plain')
        def GET(self):
            return cherrypy.session['mystring']

        def POST(self, length=8):
            some_string = ''.join(random.sample(string.hexdigits, int(length)))
            cherrypy.session['mystring'] = some_string
            return some_string

        def PUT(self, another_string):
            cherrypy.session['mystring'] = another_string

        def DELETE(self):
            cherrypy.session.pop('mystring', None)

    if __name__ == '__main__':
        conf = {
            '/': {
                'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
                'tools.sessions.on': True,
                'tools.response_headers.on': True,
                'tools.response_headers.headers': [('Content-Type', 'text/plain')],
            }
        }
        cherrypy.quickstart(StringGeneratorWebService(), '/', conf)


Save this into a file named `tut07.py` and run it as follow:

.. code-block:: bash

   $ python tut07.py

Before we see it in action, let's explain a few things. Until now,
CherryPy was creating a tree of exposed methods that were used to
math URLs. In the case of our web API, we want to stress the role
played by the actual requests' HTTP methods. So we created 
methods that are named after them and they are all exposed at once
through the `exposed = True` attribute of the class itself.

However, we must then switch from the default mechanism of matching
URLs to method for one that is aware of the whole HTTP method
shenanigan. This is what goes on line 27 where we create 
a :class:`~cherrypy.dispatch.MethodDispatcher` instance.

Then we force the responses `content-type` to be `text/plain` and
we finally ensure that `GET` requests will only be responded to clients
that accept that `content-type` by having a `Accept: text/plain` 
header set in their request. However, we do this only for that
HTTP method as it wouldn't have much meaning on the oher methods.


For the purpose of this tutorial, we will be using a Python client
rather than your browser as we wouldn't be able to actually try
our web API otherwiser.

Please install `requests <http://www.python-requests.org/en/latest/>`_
through the following command:

.. code-block:: bash

   $ pip install requests

Then fire up a Python terminal and try the following commands:

.. code-block:: pycon
   :linenos:

   >>> import requests
   >>> s = requests.Session()
   >>> r = s.get('http://127.0.0.1:8080/')
   >>> r.status_code
   500
   >>> r = s.post('http://127.0.0.1:8080/')
   >>> r.status_code, r.text
   (200, u'04A92138')
   >>> r = s.get('http://127.0.0.1:8080/')
   >>> r.status_code, r.text
   (200, u'04A92138')
   >>> r = s.get('http://127.0.0.1:8080/', headers={'Accept': 'application/json'})
   >>> r.status_code
   406
   >>> r = s.put('http://127.0.0.1:8080/', params={'another_string': 'hello'})
   >>> r = s.get('http://127.0.0.1:8080/')
   >>> r.status_code, r.text
   (200, u'hello')
   >>> r = s.delete('http://127.0.0.1:8080/')
   >>> r = s.get('http://127.0.0.1:8080/')
   >>> r.status_code
   500

The first and last `500` responses steam from the fact that, in
the first case, we haven't yet generated a string through `POST` and,
on the latter case, that it doesn't exist after we've deleted it.

Lines 12-14 show you how the application reacted when our client requested
the generated string as a JSON format. Since we configured the
web API to only support plain text, it returns the appropriate 
`HTTP error code http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html#sec10.4.7`


.. note::

   We use the `Session <http://www.python-requests.org/en/latest/user/advanced/#session-objects>`_
   interface of `requests` so that it takes care of carrying the
   session id stored in the request cookie in each subsequent
   request. That is handy.

.. _tut08:


Tutorial 8: Make it smoother with Ajax
--------------------------------------

In the recent years, web applications have moved away from the
simple pattern of "HTML forms + refresh the whole page". This 
traditional scheme still works very well but users have become used
to web applications that don't refresh the entire page. 
Broadly speaking, web applications carry code performed 
client-side that can speak with the backend without having to 
refresh the whole page.

This tutorial will involve a little more code this time around. First,
let's see our CSS stylesheet located in `public/css/style.css`.

.. code-block:: css
   :linenos:

   body { 
     background-color: blue;
   }

   #the-string { 
     display: none;
   }

We're adding a simple rule about the element that will display
the generated string. By default, let's not show it up.
Save the following HTML code into a file named `index.html`.

.. code-block:: html
   :linenos:

   <!DOCTYPE html>
   <html>
      <head>
	<link href="/static/css/style.css" rel="stylesheet">
	<script src="http://code.jquery.com/jquery-2.0.3.min.js"></script>
	<script type="text/javascript">
	  $(document).ready(function() {

	    $("#generate-string").click(function(e) {
	      $.post("/generator", {"length": $("input[name='length']").val()})
	       .done(function(string) {
		  $("#the-string").show();
		  $("#the-string input").val(string);
	       });
	      e.preventDefault();
	    });

	    $("#replace-string").click(function(e) {
	      $.ajax({
		 type: "PUT",
		 url: "/generator",
		 data: {"another_string": $("#the-string").val()}
	      })
	      .done(function() {
		 alert("Replaced!");
	      });
	      e.preventDefault();
	    });

	    $("#delete-string").click(function(e) {
	      $.ajax({
		 type: "DELETE",
		 url: "/generator"
	      })
	      .done(function() {
		 $("#the-string").hide();
	      });
	      e.preventDefault();
	    });

	  });
	</script>
      </head>
      <body>
	<input type="text" value="8" name="length" />
	<button id="generate-string">Give it now!</button>
	<div id="the-string">
	    <input type="text" />
	    <button id="replace-string">Replace</button>
	    <button id="delete-string">Delete it</button>
	</div>
      </body>
   </html>

We'll be using the `jQuery framework <http://jquery.com/>`_
out of simplicity but feel free to replace it with your
favourite tool. The page is composed of simple HTML elements
to get user input and display the generated string. It also
contains client-side code to talk to the backend API that
actually performs the hard work.

Finally, here's the application's code that serves the
HTML page above and responds to requests to generate strings.
Both are hosted by the same application server.

.. code-block:: python
   :linenos:

    import os, os.path
    import random
    import string

    import cherrypy

    class StringGenerator(object):
       @cherrypy.expose
       def index(self):
           return file('index.html')

    class StringGeneratorWebService(object):
        exposed = True

        @cherrypy.tools.accept(media='text/plain')
        def GET(self):
            return cherrypy.session['mystring']

        def POST(self, length=8):
            some_string = ''.join(random.sample(string.hexdigits, int(length)))
            cherrypy.session['mystring'] = some_string
            return some_string

        def PUT(self, another_string):
            cherrypy.session['mystring'] = another_string

        def DELETE(self):
            cherrypy.session.pop('mystring', None)

    if __name__ == '__main__':
        conf = {
            '/': {
                'tools.sessions.on': True,
                'tools.staticdir.root': os.path.abspath(os.getcwd())
            },            
            '/generator': {
                'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
                'tools.response_headers.on': True,
                'tools.response_headers.headers': [('Content-Type', 'text/plain')],
            },
            '/static': {
                'tools.staticdir.on': True,
                'tools.staticdir.dir': './public'
            }
        }
        webapp = StringGenerator()
        webapp.generator = StringGeneratorWebService()
        cherrypy.quickstart(webapp, '/', conf)


Save this into a file named `tut08.py` and run it as follow:

.. code-block:: bash

   $ python tut08.py

Go to http://127.0.0.1:8080/ and play with the input and buttons 
to generate, replace or delete the strings. Notice how the page
isn't refreshed, simply part of its content.

Notice as well how your frontend converses with the backend using
a straightfoward, yet clean, web service API. That same API
could easily be used by non-HTML clients.


Tutorial 9: Data is all my life
-------------------------------

Until now, all the generated strings were saved in the 
session, which by default is stored in the process memory. Though,
you can persist sessions on disk or in a distributed memory store,
this is not the right way of keeping your data on the long run. 
Sessions are there to identify your user and carry as little
amount of data as necessary for the operation carried by the user.

To store, persist and query data your need a proper database server.
There exist many to choose from with various paradigm support:

- relational: PostgreSQL, SQLite, MariaDB, Firebird
- column-oriented: HBase, Cassandra
- key-store: redis, memcached
- document oriented: Couchdb, MongoDB
- graph-oriented: neo4j

Let's focus on the relational ones since they are the most common
and probably what you will want to learn first. 

For the sake of reducing the number of dependencies for these
tutorials, we will go for the :mod:`sqlite` database which
is directly supported by Python. 

Our application will replace the storage of the generated
string from the session to a SQLite database. The application
will have the same HTML code as :ref:`tutorial 08 <tut08>`.
So let's simply focus on the application code itself:

.. code-block:: python
   :linenos:

    import os, os.path
    import random
    import sqlite3
    import string

    import cherrypy

    DB_STRING = "my.db"

    class StringGenerator(object):
       @cherrypy.expose
       def index(self):
           return file('index.html')

    class StringGeneratorWebService(object):
        exposed = True

        @cherrypy.tools.accept(media='text/plain')
        def GET(self):
            with sqlite3.connect(DB_STRING) as c:
                c.execute("SELECT value FROM user_string WHERE session_id=?",
                          [cherrypy.session.id])
                return c.fetchone()

        def POST(self, length=8):
            some_string = ''.join(random.sample(string.hexdigits, int(length)))
            with sqlite3.connect(DB_STRING) as c:
                c.execute("INSERT INTO user_string VALUES (?, ?)",
                          [cherrypy.session.id, some_string])
            return some_string

        def PUT(self, another_string):
            with sqlite3.connect(DB_STRING) as c:
                c.execute("UPDATE user_string SET value=? WHERE session_id=?",
                          [another_string, cherrypy.session.id])

        def DELETE(self):
            with sqlite3.connect(DB_STRING) as c:
                c.execute("DELETE FROM user_string WHERE session_id=?",
                          [cherrypy.session.id])

    def setup_database():
        """
        Create the `user_string` table in the database
        on server startup
        """
        with sqlite3.connect(DB_STRING) as con:
            con.execute("CREATE TABLE user_string (session_id, value)")

    def cleanup_database():
        """
        Destroy the `user_string` table from the database
        on server shutdown.
        """
        with sqlite3.connect(DB_STRING) as con:
            con.execute("DROP TABLE user_string")

    if __name__ == '__main__':
        conf = {
            '/': {
                'tools.sessions.on': True,
                'tools.staticdir.root': os.path.abspath(os.getcwd())
            },            
            '/generator': {
                'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
                'tools.response_headers.on': True,
                'tools.response_headers.headers': [('Content-Type', 'text/plain')],
            },
            '/static': {
                'tools.staticdir.on': True,
                'tools.staticdir.dir': './public'
            }
        }

        cherrypy.engine.subscribe('start', setup_database)
        cherrypy.engine.subscribe('stop', cleanup_database)

        webapp = StringGenerator()
        webapp.generator = StringGeneratorWebService()
        cherrypy.quickstart(webapp, '/', conf)


Save this into a file named `tut09.py` and run it as follow:

.. code-block:: bash

   $ python tut09.py

Let's first see how we create two functions that create
and destroy the table within our database. These functions
are registered to the CherryPy's server on lines 76-77,
so that they are called when the server starts and stops.

Next, notice how we replaced all the session code with calls
to the database. We use the session id to identify the
user's string within our database. Since the session will go
away after a while, it's probably not the right approach.
A better idea would be to associate the user's login or 
more resilient unique identifier. For the sake of our
demo, this should do.

.. note::

   Unfortunately, sqlite in Python forbids us
   to share a connection between threads. Since CherryPy is a 
   multi-threaded server, this would be an issue. This is the
   reason why we open and close a connection to the database
   on each call. This is clearly not really production friendly,
   and it is probably advisable to either use a more capable
   database engine or a higher level library, such as 
   `SQLAlchemy <http://sqlalchemy.readthedocs.org>`, to better
   support your application's needs.
