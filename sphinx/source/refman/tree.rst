..
    This is not ideally documented at the moment.
    
    There's no way to describe the module as it appears at runtime,
    but then reference the docstrings from the actual objects.
    
    This should really be trying to document the class cherrypy._cptree.Tree

    Would love if I could map the autodocs to the right place
    .. automethod:: cherrypy._cptree.Tree.script_name




:mod:`cherrypy.tree`
====================

.. module:: cherrypy.tree

The global registry of CherryPy applications, mounted at diverse points.

This is actually an instance of a Tree class instead of a module.
An instance may also be used as a WSGI callable (WSGI application object),
in which case it dispatches to all mounted apps.


.. function:: mount(root, script_name='', config=None)

    Mount a new app from a root object, script_name, and config.

    root: an instance of a "controller class" (a collection of page
        handler methods) which represents the root of the application.
        This may also be an Application instance, or None if using
        a dispatcher other than the default.

    script_name: a string containing the "mount point" of the application.
        This should start with a slash, and be the path portion of the
        URL at which to mount the given root. For example, if root.index()
        will handle requests to "http://www.example.com:8080/dept/app1/",
        then the script_name argument would be "/dept/app1".

        It MUST NOT end in a slash. If the script_name refers to the
        root of the URI, it MUST be an empty string (not "/").
        
    config: a file or dict containing application config.
    
.. function:: graft(wsgi_callable, script_name='')

    Mount a wsgi callable at the given script_name.

.. function:: script_name

    The script_name of the app at the given path, or None.
    
    If path is None, cherrypy.request is used.

