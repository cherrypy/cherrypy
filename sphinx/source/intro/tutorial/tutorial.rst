.. _tutorial:

Tutorial
********

This document provides a set of exercises designed to help you learn CherryPy.

What is this tutorial about?
============================

This tutorial cover the basic steps for a newcomer to get to grips with CherryPy unique approach to web application development. After following this tutorial, the programmer will be able to understand how CherryPy applications work, and also to implement simple but yet powerful applications on her own. Some knowledge of the Python programming language is assumed. One does not need to be an expert to work with CherryPy, but a good understanding of object-oriented basics is strongly recommended. 

Knowledge required
------------------

It is assumed that the user has:

 * Some knowledge of the Python programming language;
 * Some experience with basic object oriented programming;
 * Some knowledge of HTML, which is necessary to build the Web pages.

Learning Python
---------------

As said above, this is not a guide to the Python language. There are plenty of good resources for those learning Python (just to name a few among the best:  `Python course in Bioinformatics <http://www.pasteur.fr/recherche/unites/sis/formation/python/>`_, `A Byte Of Python <http://www.byteofpython.info/>`_ and `Dive into Python <http://www.diveintopython.org/>`_). The `official Python website <http://www.python.org>`_ lists some good resources, including an `excellent tutorial <http://docs.python.org/tut/tut.html>`_.

Your first CherryPy application
===============================

The standard 'Hello world!' application takes less than 10 lines of code, when written using CherryPy.::

    #!python
    import cherrypy
    
    class HelloWorld:
        def index(self):
            return "Hello world!"
        index.exposed = True
    
    cherrypy.quickstart(HelloWorld())


We assume that you already have `installed CherryPy <TODO-fix wiki target CherryPyInstall>`_. Copy this file and save it locally as ``hello.py``, then start the application at the command prompt: ::


    python hello.py


Direct your favorite web browser to http://localhost:8080 and you should see ``Hello world!`` printed there.

How does it work?
-----------------

Let's take a look at the ``hello.py``:

 * The ``import cherrypy`` statement imports the main CherryPy module. This is all that is required to have CherryPy working. Feel free to "import cherrypy" in an interactive session and see what's available! `help(cherrypy)` is also quite useful.
 * We declare a class named ``HelloWorld``. An instance of this class is the object that will be published by CherryPy. It contains a single method, named ``index``, which will get called when the root URL for the site is requested (for example, ``http://localhost/``). This method returns the '''contents''' of the Web page; in this case, the ``'Hello World!'`` string.
 * The ``index.exposed = True`` is a necessary step to tell CherryPy that the ``index()`` method will be '''exposed'''. Only exposed methods can be called to answer a request. This feature allows the user to select which methods of an object will be accessible via the Web; non-exposed methods can't be accessed.
 * ``cherrypy.quickstart(HelloWorld())`` mounts an instance of the !HelloWorld class, and starts the embedded webserver. It runs until explicitly interrupted, either with ``Ctrl-C`` or via a suitable signal (a simple ``kill`` on Unix will do it).

When the application is executed, the CherryPy server is started with the default configuration. It will listen on ``localhost`` at port ``8080``. These defaults can be overridden by using a configuration file (more on this later).

Finally, the web server receives the request for the URL ``http://localhost:8080``. It searches for the best method to handle the request, starting from the ``HelloWorld`` instance. In this particular case, the root of the site is automatically mapped to the ``index()`` method (similar to the ``index.html`` that is the standard page for conventional Web servers). The !HelloWorld class defines an ``index()`` method and exposes it. CherryPy calls ``HelloWorld().index()``, and the result of the call is sent back to the browser as the contents of the index page for the website. All work is done automatically; the application programmer only needs to provide the desired content as the return value of the ``index`` method.

Concepts
========

Any object that is attached to the root object is traversible via the internal URL-to-object mapping routine. However, it does not mean that the object itself is directly accessible via the Web. For this to happen, the object has to be '''exposed'''.

Exposing objects
----------------

CherryPy maps URL requests to objects and invokes the suitable callable automatically. The callables that can be invoked as a result of external requests are said to be '''exposed'''.

Objects are '''exposed''' in CherryPy by setting the ``exposed`` attribute. Most often, a method on an object is the callable that is to be invoked.  In this case, one can directly set the exposed attribute: ::

    #!python
    class Root:
        def index(self):
            ...
        index.exposed = True


or use a decorator: ::

    #!python
        @cherrypy.expose
        def index(self):
            ...


When it is a special method, such as ``__call__``, that is to be invoked the exposed attribute must be set on the object itself: ::

    #!python
    class Node:
        exposed = True
        def __call__(self):
            ...


Finding the correct object
==========================

For the user, a web application is just like a website with static files. The user types (or clicks) a URL, and gets to the desired webpage. A conventional webserver uses the URL to retrieve a static file from the filesystem. On the other hand, a web application server not only serves the content from static files; it can also map the URL it receives into some object and call it. The result is then sent back to the user's browser, where it is rendered into a viewable page. The result is a dynamic web application; for each URL, a unique object can be called into action.

The key to understand how to write a new web application is to understand how this mapping occurs. CherryPy uses a fairly straightforward mapping procedure. The root of the site is the ``Application.root`` object. When it receives a URL, it breaks it into its path components, and proceeds looking down into the site until it finds an object that is the 'best match' for that particular URL. For each path component it tries to find an object with the same name, starting from ``root``, and going down for each component it finds, until it can't find a match. An example shows it better: ::


    #!python
    root = HelloWorld()
    root.onepage = OnePage()
    root.otherpage = OtherPage()


In the example above, the URL ``http://localhost/onepage`` will point at the first object and the URL ``http://localhost/otherpage`` will point at the second one. As usual, this search is done automatically. But it goes even further: ::


    #!python
    root.some = Page()
    root.some.page = Page()


In this example, the URL ``http://localhost/some/page`` will be mapped to the ``root.some.page`` object. If this object is exposed (or alternatively, its ``index`` method is), it will be called for that URL.

In our !HelloWorld example, adding the ``http://.../onepage`` to ``OnePage()`` mapping could be done like this: ::


    #!python
    class OnePage(object):
        def index(self):
            return "one page!"
        index.exposed = True
 
    class HelloWorld(object):
        onepage = OnePage()
     
        def index(self):
            return "hello world"
        index.exposed = True
 
    cherrypy.quickstart(HelloWorld())


Normal methods
==============

CherryPy can directly call methods on the mounted objects, if it receives a URL that is directly mapped to them. For example: ::


    #!python
    def foo(self):
        return 'Foo!'
    foo.exposed = True
    
    root.foo = foo


In the example, ``root.foo`` contains a function object, named ``foo``. When CherryPy receives a request for the ``/foo`` URL, it will automatically call the ``foo()`` function. Note that it can be a plain function, or a method of any object; any callable will do it.

In some advanced cases, there can be a conflict as CherryPy tries to decide which method it will call to handle a request. The ``index()`` method (see below) takes precedence. But if CherryPy finds a full match, and the last object in the match is a callable (which means a method, function, or any other Python object that supports the ``__call__`` method); and finally, if the callable itself does not contain a valid ``index()`` method, then the object itself will be called. These rules are necessary because classes in Python actually are callables; calling them produces a new instance. It may look confusing, but the rules are very simple use in practice.

The `index` method
==================

The `index` method has a special role in CherryPy: it handles intermediate URI's that end in a slash; for example, the URI `/orders/items/` might map to `root.orders.items.index`. The `index` method can take additional keyword arguments if the request includes querystring or POST params; however, it ''cannot'' take positional arguments.

Receiving data from HTML forms
==============================

Any method that is called by CherryPy - ``index``, or any other suitable method - can receive additional data from HTML forms using '''keyword arguments'''. For example, the following login form sends the ``username`` and the ``password`` as form arguments using the POST method: ::


    #!text/html
    <form action="doLogin" method="post">
        <p>Username</p>
        <input type="text" name="username" value="" 
            size="15" maxlength="40"/>
        <p>Password</p>
        <input type="password" name="password" value="" 
            size="10" maxlength="40"/>
        <p><input type="submit" value="Login"/></p>
        <p><input type="reset" value="Clear"/></p>
    </form>


The following code can be used to handle this URL: ::


    #!python
    class Root:
        def doLogin(self, username=None, password=None):
            # check the username & password
            ...
        doLogin.exposed = True


Both arguments have to be declared as '''keyword arguments'''. The default value can be used either to provide a suitable default value for optional arguments, or to provide means for the application to detect if some values were missing from the request.

CherryPy supports both the GET and POST method for HTML forms. Arguments are passed the same way, regardless of the original method used by the browser to send data to the web server.

Partial matches and the default method
======================================

Partial matches can happen when a URL contains components that do not map to the object tree. This can happen for a number of reasons. For example, it may be an error; the user just typed the wrong URL. But it also can mean that the URL contains extra arguments.

When a partial match happens, CherryPy calls a ``default`` method. The ``default`` method is similar to the ``index`` method; however, it is only called as a last resort method, and it's recommended for two applications:

 * Error handling, to be called when the user types the wrong URL;
 * Support for positional arguments (since CherryPy 2.2, positional arguments can be used with all methods except index).

For example, assume that you have a blog-like application written in CherryPy that takes the year, month and day as part of the URL ``http://localhost/blog/2005/01/17``. This URL can be handled by the following code: ::


    #!python
    class Blog:
        def default(self, year, month, day):
            ...
        default.exposed = True
    ...
    root.blog = Blog()


So the URL above will be mapped as a call to: ::


    #!python
    root.blog.default('2005', '1', '17')


In this case, there is a partial match up to the ``blog`` component. The rest of the URL can't be found in the mounted object tree. In this case, the ``default()`` method will be called, and the positional parameters will receive the remaining path components as arguments. The values are passed as strings; in the above mentioned example, the arguments would still need to be converted back into numbers, but the idea is correctly presented.

The CherryPy configuration file
===============================

CherryPy uses a simple `configuration file <TODO-fix wiki target ConfigAPI>`_ format to customize some aspects of its behavior. There are actually two (or more) files, one for the global "site" and one for each "application"; but if you only have one app you can put them both in the same file. The configuration files can be edited with any conventional text editor, and can be used even by non-technical users for some simple customization tasks. For example: ::

    [global]
    server.socket_port = 8000
    server.thread_pool = 10
    tools.sessions.on = True
    tools.staticdir.root = "/home/site"

    [/static]
    tools.staticdir.on = True
    tools.staticdir.dir = "static"


Many of the values are self explanatory (for example, ``server.socket_port``, which allows changing the default port at which CherryPy listens); others need a better understanding of CherryPy internals. 

 * The ``server.thread_pool`` option determines how many threads CherryPy starts to serve requests.
 * The ``tools.sessions.on`` statement enables the session functionality. Sessions are necessary to implement complex Web applications, with user identification, for example.
 * The ``[/static]`` statement specifies that static content from /home/site/static/* is served as /static/*
 * The ``tools.staticdir.root`` statement specifies the directory from which the static files are served. See StaticContent.

If you're using quickstart, you can pass a single configuration filename (or dict) containing both site and app config to ``cherrypy.quickstart(Root(), '/', filename_or_dict)``. Otherwise, you need to register global site config as ``cherrypy.config.update(filename_or_dict)`` and app config in ``cherrypy.tree.mount(Root(), '/', filename_or_dict)``. See the `config docs <TODO-fix wiki target ConfigAPI>`_ for more information.

The CherryPy structure
======================

Most of the features of CherryPy are available through the ``cherrypy`` module. It contains several members:

 * ``cherrypy.engine`` contains the API to control the CherryPy engine.
 * ``cherrypy.server`` contains the API to control the HTTP server.
 * `cherrypy.request <TODO-fix wiki target RequestObject>`_ contains the all the information that comes with the HTTP request, after it is parsed and analyzed by CherryPy.
 * ``cherrypy.request.headers`` contains a mapping with the header options that were sent as part of the request.
 * ``cherrypy.session`` is a special mapping that is automatically generated and encoded by CherryPy; it can be used to store session-data in a persistent cookie. For it to work you have to enable the session functionality by setting 'tools.session.on' to True in your config. 
 * `cherrypy.response <TODO-fix wiki target ResponseObject>`_ contains the data that is used to build the HTTP response. 
 * ``cherrypy.response.headers`` contains a mapping with the header options that will be returned by the server, before the contents get sent.
 * ``cherrypy.response.body`` contains the actual contents of the webpage that will be sent as a response.

Tools
=====

CherryPy core is extremely light and clean. It contains only the necessary features to support the HTTP protocol and to call the correct object for each request. Additional features can be added to it using '''modular tools'''.

A tool is an object that has a chance to work on a request as it goes through the usual CherryPy processing chain. Several tools are provided as part of the standard CherryPy library, available in ``cherrypy.tools``. Some examples are:

 * tools.decode: automatically handles Unicode data on the request, converting the raw strings that are sent by the browser into native Python strings.
 * tools.encode: automatically converts the response from the native Python Unicode string format to some suitable encoding (Latin-1 or UTF-8, for example).
 * tools.gzip: Compresses the contents on the fly, using the ``gzip`` format. Saves bandwidth.
 * tools.xmlrpc: Implements a special XML-RPC adaptation layer over the standard CherryPy. It takes care of translating the data on request and response (a process called 'marshalling').

Tools provide a lot of flexibility. Different tools can be applied to different parts of the site, and the order of tools can be changed. The user can write custom tools for special applications, changing the behavior of CherryPy without the need to change its internals.

The tools for any part of the site are usually enabled in the configuration file: ::

    [/]
    tools.encode.on = True
    tools.gzip.on = True


In this case, the application can use Unicode strings for the contents it generates; translation to ``utf8`` will be done automatically via the encoding tool. Also, all the content will be automatically compressed with gzip, saving bandwidth.

Conclusion
==========

This tutorial only covers the basic features of CherryPy, but it tries to present them in a way that makes it easier for the user to discover how to use them. The CherryPy distribution comes with several good tutorials; however, the best way to master CherryPy is to use it to write your own Web applications. The embedded web server makes it easy for anyone not only to try, but also to deploy local applications, or even small Internet-enabled web sites. Try it, and let us know what you did with it! ::

    #!html
    <h2 class='compatibility'>Older versions</h2>

||   || replace this  || with this ||
||2.2||cherrypy.quickstart(HelloWorld())||cherrypy.root = HelloWorld()[[br]]cherrypy.server.start()||
||   ||tools.sessions ||session_filter||
||   ||tools.staticdir||static_filter ||
||2.1||simple_cookie  ||simpleCookie  ||
||   ||socket_port    ||socketPort    ||
||   ||thread_pool    ||threadPool    ||
||   ||session_filter ||sessionFilter ||
||   ||static_filter  ||staticFilter  ||
||   ||headers        ||headerMap     ||
||2.0||import cherrypy||from cherrypy import cpg as cherrypy||
