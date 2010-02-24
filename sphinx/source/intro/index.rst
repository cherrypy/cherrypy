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
problem. CherryPy applications are usually very simple. It works out of the
box; default behavior is sensible enough to allow use without extensive setup
or customization. The embedded web server allows one to deploy web applications
anywhere Python is installed. In short, CherryPy is as pythonic as it gets.

CherryPy is now more than six years old and it is has proven very fast and
stable. It is being used in production by many sites, from the simplest ones
to the most demanding ones.

Oh, and most importantly: CherryPy is fun to work with :-)
Here's how easy it is to write "Hello World" in CherryPy 3::

    import cherrypy

    class HelloWorld(object):
        def index(self):
            return "Hello World!"
        index.exposed = True

    cherrypy.quickstart(HelloWorld())


What CherryPy is NOT?
=====================

As an HTTP framework, CherryPy does all that is necessary to allow Python code
to be executed when some resource (or URL) is requested by the user. However,
it is not a templating language, such as PHP. CherryPy can work with several
templating packages (see :doc:`/progguide/choosingtemplate`). But please note
that, while useful to some extent, templating packages are not strictly
necessary, and that pure Python code can be used to generate the Web pages.

Quick Facts
===========

    * Your CherryPy powered web applications are in fact stand-alone Python
      applications embedding their own multi-threaded web server. You can
      deploy them anywhere you can run Python applications. Apache is not
      required, but it's possible to run a CherryPy application behind it
      (or lighttpd, or nginx, or IIS). CherryPy applications run on Windows,
      Linux, Mac OS X and any other platform supporting Python.
    * You write request handler classes that you tie together in a tree of
      objects, starting with a root object. CherryPy maps incoming request
      URIs to this object tree. The URI '/' represents the 'root' object,
      '/users/' the 'root.users' object, and so on. Requests are handled by
      methods inside these request handler classes. GET/POST parameters are
      passed as standard method parameters; '/users/display?id=123' will call
      root.users.display(id = '123'). The methods' return strings are then
      passed back to the browser. You have complete control over which methods
      are exposed through the web and which ones aren't. [And if you don't like
      any of the above, you can swap any part of it out!]
    * Beyond this functionality, CherryPy pretty much stays out of your way.
      You are free to use any kind of templating, data access etc. technology
      you want. CherryPy can also handle sessions, static files, cookies,
      file uploads and everything you would expect from a decent web framework.

Features
========

    * A fast, HTTP/1.1-compliant, WSGI thread-pooled webserver. Typically,
      CherryPy itself takes only 1-2ms per page!
    * Support for any other WSGI-enabled webserver or adapter, including
      Apache, IIS, lighttpd, mod_python, FastCGI, SCGI, and mod_wsgi
    * Easy to run multiple HTTP servers (e.g. on multiple ports) at once
    * A powerful configuration system for developers and deployers alike
    * A flexible plugin system
    * Built-in tools for caching, encoding, sessions, authorization, static
      content, and many more
    * A native mod_python adapter
    * A complete test suite
    * Swappable and customizable...everything.
    * Built-in profiling, coverage, and testing support.

Contents
========

.. toctree::
   :maxdepth: 2
   :glob:

   whycherrypy
   install
   tutorial/*
   concepts/index
   license


