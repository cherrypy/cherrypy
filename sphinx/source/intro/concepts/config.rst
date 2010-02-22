*************
Configuration
*************

Configuration in CherryPy is implemented via dictionaries. Keys are strings which name the mapped value; values may be of any type.

In CherryPy 3, you use configuration (files or dicts) to set attributes directly on the engine, server, request, response, and log objects. So the best way to know the full range of what's available in the config file is to simply import those objects and see what ``help(obj)`` tells you.

Architecture
============

The first thing you need to know about CherryPy 3's configuration is that it now separates *site* config from *app* config. If you're deploying multiple *applications* at the same *site* (and more and more people are, as Python web apps are tending to decentralize), you need to be careful to separate the configurations, as well. There's only ever one "site config", but there is a separate "app config" for each app you deploy.

CherryPy *Requests* are part of an *Application*, which runs in a *global* context, and configuration data may apply to any of those three scopes.


Site config
===========

Site config entries apply everywhere, and are stored in cherrypy.config. This flat dict only holds global config data; that is, "site-wide" config entries which affect all mounted applications.

Site config is stored in the ``cherrypy.config`` dict, and you therefore update it by calling ``cherrypy.config.update(conf)``. The ``conf`` argument can be either a filename, an open file, or a dict of config entries. Here's an example of passing a dict argument::

    cherrypy.config.update({'server.socket_host': '64.72.221.48',
                            'server.socket_port': 80,
                           })

Application config
==================

Application entries apply to a single mounted application, and are stored on each Application object itself as ``app.config``. This is a two-level dict where each key is a path, or "relative URL" (for example, ``"/"`` or ``"/my/page"``), and each value is a config dict. The URL's are relative to the "script name" of the Application. Usually, all this data is provided in the call to ``tree.mount(root(), script_name='/path/to', config=conf)``, although you may also use ``app.merge(conf)``. The ``conf`` argument can be either a filename, an open file, or a dict of config entries.

Examples::

    tools.trailing_slash.on = False
    request.dispatch: cherrypy.dispatch.MethodDispatcher()

or in python::

    config = {'/': 
        {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.trailing_slash.on': False,
        }
    }
    cherrypy.tree.mount(Root(), "/script_name_root", config=config)

CherryPy doesn't use any sections that don't start with ``"/"`` (except ``[global]``, see below). That means you can place your own configuration entries in a CherryPy config file by giving them a section name which does not start with ``"/"``. For example, you might include database entries like this:

.. code-block:: cfg

    [global]
    server.socket_host: "0.0.0.0"

    [Databases]
    driver: "postgres"
    host: "localhost"
    port: 5432

    [/path]
    response.timeout: 6000

Then, in your application code you can read these values during request time via ``cherrypy.request.app.config['Databases']``. For code that is outside the request process, you'll have to pass a reference to your Application.

Request config
--------------

Each Request object possesses a single ``request.config`` dict. Early in the request process, this dict is populated by merging site config, Application config, and any config acquired while looking up the page handler (see next). This dict contains only those config entries which apply to the given request; that is, per-path config. Note that when you do an InternalRedirect, this config is recalculated for the new path.

Declaration
===========

Configuration data may be supplied as a Python dictionary, as a filename, or as an open file object.

Configuration files
-------------------

When you supply a filename or file, CherryPy uses Python's builtin !ConfigParser; you declare Application config by writing each path as a section header, and each entry as a ``"key: value"`` (or ``"key = value"``) pair:

.. code-block:: cfg

    [/path/to/my/page]
    response.stream: True
    tools.trailing_slash.extra = False

Combined Configuration Files
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you are only deploying a single application, you can make a single config file that contains both site and app entries. Just stick the site entries into a config section named ``[global]``, and pass the same file to both ``update`` and ``mount``. If you're calling ``cherrypy.quickstart(app root, script name, config)``, it will pass the config to both places for you. But as soon as you decide to add another application to the same site, you need to separate the two config files/dicts.

Separate Configuration Files
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you're deploying more than one application in the same process, you need (1) file for site-wide config, plus (1) file for *each* Application. The site-wide config is applied by calling ``cherrypy.config.update``, and application config is usually passed in a call to ``cherrypy.tree.mount(root, script_name, config)``.

In general, you should set global (site-wide) config first, and then mount each application with its own config. Among other benefits, this allows you to set up site-level logging so that, if something goes wrong while trying to mount an application, you'll see the tracebacks. In other words, use this order::

    # Site-wide (global) config
    cherrypy.config.update({'environment': 'production',
                            'log.error_file': 'site.log',
                            # ...
                            })

    # Mount each app and pass it its own config
    cherrypy.tree.mount(root1, "/", appconf1)
    cherrypy.tree.mount(root2, "/forum", appconf2)
    cherrypy.tree.mount(root3, "/blog", appconf3)

    if hasattr(cherrypy.engine, 'block'):
        # 3.1 syntax
        cherrypy.engine.start()
        cherrypy.engine.block()
    else:
        # 3.0 syntax
        cherrypy.server.quickstart()
        cherrypy.engine.start()

Values in config files use Python syntax
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Config entries are always a key/value pair, like ``server.socket_port = 8080``. The key is always a name, and the value is always a Python object. That is, if the value you are setting is an ``int`` (or other number), it needs to look like a Python ``int``; for example, ``8080``. If the value is a string, it needs to be quoted, just like a Python string. Arbitrary objects can also be created, just like in Python code (assuming they can be found/imported). Here's an extended example, showing you some of the different types:

.. code-block:: cfg

    [global]
    log.error_file: "/home/fumanchu/myapp.log"
    environment = 'production'
    server.max_request_body_size: 1200

    [/myapp]
    tools.trailing_slash.on = False
    request.dispatch: cherrypy.dispatch.MethodDispatcher()

_cp_config: attaching config to handlers
----------------------------------------

Config files have a severe limitation: values are always keyed by URL. For example:

.. code-block:: cfg

    [/path/to/page]
    methods_with_bodies = ("POST", "PUT", "PROPPATCH")

It's obvious that the extra method is the norm for that path; in fact, the code could be considered broken without it. In CherryPy 3, you can attach that bit of config directly on the page handler::

    def page(self):
        return "Hello, world!"
    page.exposed = True
    page._cp_config = {"request.methods_with_bodies": ("POST", "PUT", "PROPPATCH")}

``_cp_config`` is a reserved attribute which the dispatcher looks for at each node in the object tree. The ``_cp_config`` attribute must be a CherryPy config dictionary. If the dispatcher finds a ``_cp_config`` attribute, it merges that dictionary into the rest of the config. The entire merged config dictionary is placed in ``cherrypy.request.config``

This can be done at any point in the cherrypy tree; for example, we could have attached that config to a class which contains the page method::

    class SetOPages:

        _cp_config = {"request.methods_with_bodies": ("POST", "PUT", "PROPPATCH")}

        def page(self):
            return "Hullo, Werld!"
        page.exposed = True

Note, however, that this behavior is only guaranteed for the default dispatcher. Other dispatchers may have different restrictions on where you can attach _cp_config attributes.

This technique allows you to:

* Put config near where it's used for improved readability and maintainability.
* Attach config to objects instead of URL's. This allows multiple URL's to point to the same object, yet you only need to define the config once.
* Provide defaults which are still overridable in a config file.


Namespaces
==========

Because config entries usually just set attributes on objects, they're almost all of the form: ``object.attribute``. A few are of the form: ``object.subobject.attribute``. They look like normal Python attribute chains, because they work like them. We call the first name in the chain the *"config namespace"*. When you provide a config entry, it is bound as early as possible to the actual object referenced by the namespace; for example, the entry ``response.stream`` actually sets the ``stream`` attribute of cherrypy.response. In this way, you can easily determine the default value by firing up a python interpreter and typing::

    >>> import cherrypy
    >>> cherrypy.response.stream
    False

Each config namespace has its own handler; for example, the "request." namespace has a handler which takes your config entry and sets that value on the appropriate "request" attribute. There are a few namespaces, however, which don't work like normal attributes behind the scenes; however, they still use dotted keys and are considered to "have a namespace". You can write and register your own namespace handlers to do almost anything if you need to; see the "namespaces" attributes of the Request, Application, and ``cherrypy.config`` objects.

You can define your own namespaces to be called at the Global, Application, or Request level, by adding a named handler to ``cherrypy.config.namespaces``, ``app.namespaces``, or ``app.request_class.namespaces``. The name can be any string, and the handler must be either a callable or a (Python 2.5 style) context manager.

Environments
------------

The only key that does not exist in a namespace is the *"environment"* entry. This special entry *imports* other config entries from a template stored in ``cherrypy._cpconfig.environments[environment]``. It only applies to the global config, and only when you use ``cherrypy.config.update``.

If you find the set of existing environments (production, staging, etc) too limiting or just plain wrong, feel free to extend them or add new environments::

    cherrypy._cpconfig.environments['staging']['log.screen'] = False

    cherrypy._cpconfig.environments['Greek'] = {
        'tools.encode.encoding': 'ISO-8859-7',
        'tools.decode.encoding': 'ISO-8859-7',
        }

Builtin namespaces
------------------


========    =======================
engine      Controls the 'application engine', including autoreload. These can only be declared in the global config.
hooks       Declares additional request-processing functions.
log         Configures the logging for each application. These can only be declared in the global or / config.
request     Adds attributes to each Request.
response    Adds attributes to each Response.
server      Controls the default HTTP server via cherrypy.server. These can only be declared in the global config.
tools       Runs and configures additional request-processing packages.
wsgi        Adds WSGI middleware to an Application's "pipeline". These can only be declared in the app's root config ("/").
checker     Controls the 'checker', which looks for common errors in app state (including config) when the engine starts. Global config only.
========    =======================

Entries from each namespace may be allowed in the global, application root (``"/"``) or per-path config, or a combination:

==========  ======  ==================  =========
Scope       Global  Application Root    App Path
----------  ------  ------------------  ---------
engine      X
hooks       X       X                   X
log         X       X
request     X       X                   X
response    X       X                   X
server      X
tools       X       X                   X
==========  ======  ==================  =========

Custom config namespaces
------------------------

You can define your own namespaces if you like, and they can do far more than simply set attributes. The ``test/test_config`` module, for example, shows an example of a custom namespace that coerces incoming params and outgoing body content. The ``_cpwsgi`` module includes an additional, builtin namespace for invoking WSGI middleware.

In essence, a config namespace handler is just a function, that gets passed any config entries in its namespace. You add it to a namespaces registry (a dict), where keys are namespace names and values are handler functions. When a config entry for your namespace is encountered, the corresponding handler function will be called, passing the config key and value; that is, ``namespaces[namespace](k, v)``. For example, if you write::

    def db_namespace(k, v):
        if k == 'connstring':
            orm.connect(v)
    cherrypy.config.namespaces['db'] = db_namespace

then ``cherrypy.config.update({"db.connstring": "Oracle:host=1.10.100.200;sid=TEST"})`` will call ``db_namespace('connstring', 'Oracle:host=1.10.100.200;sid=TEST')``.

The point at which your namespace handler is called depends on where you add it:

================================    ===================================
Namespace                           Handler is called in  
--------------------------------    -----------------------------------
config.namespaces                   cherrypy.config.update
Application.namespaces              Application.merge (which is called by cherrypy.tree.mount)
engine.request_class.namespaces     Request.configure (called for each request, after the handler is looked up)
================================    ===================================

If you need additional code to run when all your namespace keys are collected, you can supply a callable context manager in place of a normal function for the handler. Context managers are defined in `PEP 343 <http://www.python.org/dev/peps/pep-0343/>`_.

