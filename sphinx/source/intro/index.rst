************
Introduction
************

What is CherryPy?
=================

CherryPy is a pythonic, object-oriented HTTP framework.

CherryPy allows developers to build web applications in much the same way they
would build any other object-oriented Python program. This results in smaller
source code developed in less time.

CherryPy does its best to stay out of the way between the programmer and the
problem. It works out of the box; default behavior is sensible enough to allow
use without extensive setup or customization. However, its configuration
and plugin systems are more than enough to easily build and deploy complex
sites.

You are free to use any kind of templating, data access etc. technology
you want. CherryPy also has built-in tools for sessions, static files, cookies,
file uploads, caching, encoding, authorization, compression, and many more.

The production-ready, HTTP/1.1-compliant web server allows you to deploy
web applications anywhere Python is installed. It also supports any other
WSGI-enabled webserver or adapter, including Apache, IIS, lighttpd, mod_python,
FastCGI, SCGI, and mod_wsgi, even multiple ones. And it's *fast*;  typically,
CherryPy itself takes only 1-2ms per request! It is being used in production
by many sites, from the simplest to the most demanding.

CherryPy applications run on Windows, Linux, Mac OS X and any other platform
supporting Python 2.3 or higher.

CherryPy is now more than eight years old and it is has proven very fast and
stable. It is well tested, and includes tools for testing, profiling, and
coverage of your own applications.

Oh, and most importantly: CherryPy is fun to work with :-)
Here's how easy it is to write "Hello World" in CherryPy::

    import cherrypy

    class HelloWorld(object):
        def index(self):
            return "Hello World!"
        index.exposed = True

    cherrypy.quickstart(HelloWorld())


What CherryPy is NOT?
=====================

As an HTTP framework, CherryPy does all that is necessary to allow Python code
to be executed when some resource (URL) is requested by the user. However:

 * CherryPy is not a templating language, such as PHP. CherryPy can work with
   several Python templating packages (see :doc:`/progguide/choosingtemplate`),
   but does not ship one by default.
 * CherryPy does not fill out HTML forms for you. You're free to use formencode
   or any other solution, or none at all if you're not using HTML ;)
 * CherryPy is not a database or ORM. Rather than dictate or bless a persistence
   layer to you, CherryPy allows you to choose your own.


Contents
========

.. toctree::
   :maxdepth: 3
   :glob:

   whycherrypy
   install
   concepts/index
   license


