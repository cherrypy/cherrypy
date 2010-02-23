***********
Dispatching
***********

    The resource is not the storage object. The resource is not a mechanism that the server uses to handle the storage object. The resource is a conceptual mapping -- the server receives the identifier (which identifies the mapping) and applies it to its current mapping implementation (usually a combination of collection-specific deep tree traversal and/or hash tables) to find the currently responsible handler implementation and the handler implementation then selects the appropriate action+response based on the request content. All of these implementation-specific issues are hidden behind the Web interface; their nature cannot be assumed by a client that only has access through the Web interface.

    `Roy Fielding <http://www.ics.uci.edu/~fielding/pubs/dissertation/evaluation.htm>`_


When you wish to serve a resource on the Web, you never actually serve the resource, because "resources" are concepts. What you serve are representations of a resource, and *page handlers* are what you use in CherryPy to do that. Page handlers are functions that you write; CherryPy calls one for each request and uses its response, often a string of HTML, as the representation.

CherryPy takes the output of the appropriate page handler function, binds it to :attr:`cherrypy.response.body`, and sends it as the HTTP response entity body. Your page handler function (and almost any other part of CherryPy) can directly set :attr:`cherrypy.response.status` and :attr:`cherrypy.response.headers` as desired.

Dispatchers
===========

Before CherryPy can call your page handlers, it has to know 1) where they are, and 2) which one to call for a given 'identifier' (URI). In CherryPy, we use a Dispatcher object to:

1. Understand the arrangement of handlers
2. Find the appropriate page handler function
3. Wrap your actual handler function in a :class:`PageHandler` object (see below)
4. Set :attr:`cherrypy.request.handler` (to the :class:`PageHandler` wrapper)
5. Collect configuration entries into :attr:`cherrypy.request.config`
6. Collect "virtual path" components

CherryPy 3 has a default arrangement of handlers (see next), but also allows you to trade it for any arrangement you can think up and implement.

Default Dispatcher
------------------

The default CherryPy :class:`Dispatcher` uses a tree of handlers, and stores the root of the tree at :attr:`Application.root`. For example::

    class Root:
        def index(self):
            return "Hello!"
        index.exposed = True

    class Branch:
        def index(self):
            return "Howdy"
        index.exposed = True
         
        def default(self, attr='abc'):
            return attr.upper()
        default.exposed = True
        
        def leaf(self, size):
            return str(int(size) + 3)
        leaf.exposed = True

    root = Root()
    root.branch = Branch()
    app = cherrypy.tree.mount(root, script_name='/')

When a request is processed, the URI is split into its components, and each one is matched in order against the nodes in the tree. Any trailing components are "virtual path" components and are passed as positional arguments. Given the example application above, the URI ``"/branch/leaf/4"`` would result in the call: ``app.root.branch.leaf(4)``.

Index methods
^^^^^^^^^^^^^

The default dispatcher will always try to find a method named `index` at the end of the branch traversal. In the example above, the URI "/branch/" would result in the call: ``app.root.branch.index()``. Depending on the use of the *trailing_slash* Tool, that might be interrupted with an HTTPRedirect, but otherwise, both ``"/branch"`` (no trailing slash) and ``"/branch/"`` (trailing slash) will result in the same call.

Index methods, unlike all other page handler methods, cannot take "virtual path" components as arguments.

Default methods
^^^^^^^^^^^^^^^

If the default dispatcher is not able to locate a suitable page handler by walking down the tree, it has a last-ditch option: it starts walking back ''up'' the tree looking for `default` methods. Default methods allow you to write handlers which accept *any* arguments, so that, for example, ``"/branch/Napoleon"`` would call ``app.root.branch.default("Napoleon")`` in our example above. You could achieve the same effect by defining a ``__call__`` method in this case, but "default" just reads better. ;)

URI's with file extensions
^^^^^^^^^^^^^^^^^^^^^^^^^^

You can use dots in a URI like ``/path/to/my.html``, but Python method names don't allow dots. To work around this, the default dispatcher converts all dots in the URI to underscores before trying to find the page handler. In the example, therefore, you would name your page handler "def my_html". However, this means the page is also available at the URI ``/path/to/my_html``. If you need to protect the resource (e.g. with authentication), **you must protect both URLs**.

Other Dispatchers
-----------------

But Mr. Fielding mentions two kinds of "mapping implementations" above: trees and hash tables ('dicts' in Python). Some web developers claim trees are difficult to change as an application evolves, and prefer to use dicts (or a list of tuples) instead. Under these schemes, the mapping key is often a regular expression, and the value is the handler function. For example::

    def root_index(name):
        return "Hello, %s!" % name

    def branch_leaf(size):
        return str(int(size) + 3)

    mappings = [
        (r'^/([^/]+)$', root_index),
        (r'^/branch/leaf/(\d+)$', branch_leaf),
        ]

CherryPy allows you to use a :class:`Dispatcher` other than the default if you wish. By using another :class:`Dispatcher` (or writing your own), you gain complete control over the arrangement and behavior of your page handlers (and config). To use another dispatcher, set the ``request.dispatch`` config entry to the dispatcher you like::

    d = cherrypy.dispatch.RoutesDispatcher()
    d.connect(name='hounslow', route='hounslow', controller=City('Hounslow'))
    d.connect(name='surbiton', route='surbiton', controller=City('Surbiton'),
              action='index', conditions=dict(method=['GET']))
    d.mapper.connect('surbiton', controller='surbiton',
                     action='update', conditions=dict(method=['POST']))

    conf = {'/': {'request.dispatch': d}}
    cherrypy.tree.mount(root=None, config=conf)

A couple of notes about the example above:

* Since Routes has no controller hierarchy, there's nothing to pass as a root to :func:`cherrypy.tree.mount`; pass ``None`` in this case.
* Usually you'll use the same dispatcher for an entire app, so specifying it at the root ("/") is common. But you can use different dispatchers for different paths if you like.
* Because the dispatcher is so critical to finding handlers (and their ancestors), this is one of the few cases where you *cannot* use :attr:`_cp_config`; it's a chicken-and-egg problem: you can't ask a handler you haven't found yet how it wants to be found.
* Since Routes are explicit, there's no need to set the ``exposed`` attribute. **All routes are always exposed.**

CherryPy ships with additional Dispatchers in :mod:`cherrypy.dispatch`.

.. _pagehandlers:

PageHandler Objects
===================

Because the Dispatcher sets ``cherrypy.request.handler``, it can also control the input and output of that handler function by wrapping the actual handler. The default Dispatcher passes "virtual path" components as positional arguments and passes query-string and entity (GET and POST) parameters as keyword arguments. It uses a PageHandler object for this, which looks a lot like::

    class PageHandler(object):
        """Callable which sets response.body."""
        
        def __init__(self, callable, *args, **kwargs):
            self.callable = callable
            self.args = args
            self.kwargs = kwargs
        
        def __call__(self):
            return self.callable(*self.args, **self.kwargs)

The actual default PageHandler is a little bit more complicated (because the args and kwargs are bound later), but you get the idea. And you can see how easy it would be to provide your own behavior, whether your own inputs or your own way of modifying the output. Remember, whatever is returned from the handler will be bound to :attr:`cherrypy.response.body` and will be used as the response entity.

Replacing page handlers
-----------------------

The handler that's going to be called during a request is available at :attr:`cherrypy.request.handler`, which means your code has a chance to replace it before the handler runs. It's a snap to write a Tool to do so with a :class:`HandlerWrapperTool` class::

    to_skip = (KeyboardInterrupt, SystemException, cherrypy.HTTPRedirect)
    def PgSQLWrapper(next_handler, *args, **kwargs):
        trans.begin()
        try:
            result = next_handler(*args, **kwargs)
            trans.commit()
        except Exception, e:
            if not isinstance(e, to_skip):
                trans.rollback()
            raise
        trans.end()
        return result

    cherrypy.tools.pgsql = cherrypy._cptools.HandlerWrapperTool(PgSQLWrapper)

Configuration
=============

The default arrangement of CherryPy handlers is a tree. This enables a very powerful configuration technique: config can be attached to a node in the tree and cascade down to all children of that node. Since the mapping of URI's to handlers is not always 1:1, this provides a flexibility which is not as easily definable in other, flatter arrangements.

However, because the arrangement of config is directly related to the arrangement of handlers, it is the responsibility of the Dispatcher to collect per-handler config, merge it with per-URI and global config, and bind the resulting dict to :attr:`cherrypy.request.config`. This dict is of depth 1 and will contain all config entries which are in effect for the current request.

