***********
Dispatching
***********

    The resource is not the storage object. The resource is not a mechanism
    that the server uses to handle the storage object. The resource is a
    conceptual mapping -- the server receives the identifier (which identifies
    the mapping) and applies it to its current mapping implementation (usually
    a combination of collection-specific deep tree traversal and/or hash tables)
    to find the currently responsible handler implementation and the handler
    implementation then selects the appropriate action+response based on the
    request content. All of these implementation-specific issues are hidden
    behind the Web interface; their nature cannot be assumed by a client that
    only has access through the Web interface.
    
    `Roy Fielding <http://www.ics.uci.edu/~fielding/pubs/dissertation/evaluation.htm>`_

When you wish to serve a resource on the Web, you never actually serve the
resource, because "resources" are concepts. What you serve are representations
of a resource, and *page handlers* are what you use in CherryPy to do that.
Page handlers are functions that you write; CherryPy calls one for each
request and uses its response (a string of HTML, for example) as the
representation.

For the user, a web application is just like a website with static files.
The user types (or clicks) a URL, and gets to the desired webpage. A
conventional webserver uses the URL to retrieve a static file from the
filesystem. A web application server, on the other hand, not only serves
the content from static files; it can also map the URL it receives into some
object and call it. The result is then sent back to the user's browser,
where it is rendered into a viewable page. The result is a dynamic web
application; for each URL, a unique object can be called into action.
The key to understand how to write a new web application is to understand
how this mapping occurs.

CherryPy takes the output of the appropriate page handler function, binds it
to :attr:`cherrypy.response.body <cherrypy._cprequest.Response.body>`,
and sends it as the HTTP response entity
body. Your page handler function (and almost any other part of CherryPy) can
directly set :attr:`cherrypy.response.status <cherrypy._cprequest.Response.status>`
and :attr:`cherrypy.response.headers <cherrypy._cprequest.Response.headers>`
as desired.

Dispatchers
===========

Before CherryPy can call your page handlers, it has to know 1) where they are,
and 2) which one to call for a given 'identifier' (URI). In CherryPy, we use
a Dispatcher object to:

1. Understand the arrangement of handlers
2. Find the appropriate page handler function
3. Wrap your actual handler function in a
   :class:`PageHandler <cherrypy._cpdispatch.PageHandler>` object (see below)
4. Set :attr:`cherrypy.request.handler <cherrypy._cprequest.Request.handler>`
   (to the :class:`PageHandler <cherrypy._cpdispatch.PageHandler>` wrapper)
5. Collect configuration entries into
   :attr:`cherrypy.request.config <cherrypy._cprequest.Request.config>`
6. Collect "virtual path" components

CherryPy has a default arrangement of handlers (see next), but also allows you
to trade it for any arrangement you can think up and implement.

Default Dispatcher
------------------

By default, CherryPy uses a fairly straightforward mapping procedure. The root
of the site is the :attr:`Application.root <cherrypy._cptree.Application.root>`
object. When it receives a URL, it breaks it into its path components, and
proceeds looking down into the site until it finds an object that is the
'best match' for that particular URL. For each path component it tries to find
an object with the same name, starting from ``root``, and going down for each
component it finds, until it can't find a match. An example shows it better::

    root = HelloWorld()
    root.onepage = OnePage()
    root.otherpage = OtherPage()

In the example above, the URL ``http://localhost/onepage`` will point at the
first object and the URL ``http://localhost/otherpage`` will point at the
second one. As usual, this search is done automatically. But it goes even further::

    root.some = Page()
    root.some.page = Page()

In this example, the URL ``http://localhost/some/page`` will be mapped to the
``root.some.page`` object. If this object is exposed (or alternatively, its
``index`` method is), it will be called for that URL.

In our HelloWorld example, adding the ``http://onepage/`` mapping
to ``OnePage().index`` could be done like this::

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
^^^^^^^^^^^^^^^

.. index:: methods; normal

CherryPy can directly call methods on the mounted objects, if it receives a
URL that is directly mapped to them. For example::

    def foo(self):
        return 'Foo!'
    foo.exposed = True
    
    root.foo = foo

In the example, ``root.foo`` contains a function object, named ``foo``. When
CherryPy receives a request for the ``/foo`` URL, it will automatically call
the ``foo()`` function. Note that it can be a plain function, or a method of
any object; any callable will do it.

.. _indexmethods:

Index methods
^^^^^^^^^^^^^

.. index:: index, methods; index

The ``index`` method has a special role in CherryPy: it handles intermediate
URI's that end in a slash; for example, the URI ``/orders/items/`` might map
to ``root.orders.items.index``. The ``index`` method can take additional
keyword arguments if the request includes querystring or POST params; see
:ref:`kwargs`, next. However,
unlike all other page handlers, it *cannot* take positional arguments (see
:ref:`args`, below).

The default dispatcher will always try to find a method named `index` at the
end of the branch traversal. In the example above, the URI "/onepage/" would
result in the call: ``app.root.onepage.index()``. Depending on the use of the
:func:`trailing_slash Tool <cherrypy.lib.cptools.trailing_slash>`,
that might be interrupted with an HTTPRedirect, but
otherwise, both ``"/onepage"`` (no trailing slash) and ``"/onepage/"``
(trailing slash) will result in the same call.

.. _kwargs:

Keyword Arguments
^^^^^^^^^^^^^^^^^

.. index:: forms, **kwargs

Any page handler that is called by CherryPy (``index``, or any other suitable
method) can receive additional data from HTML or other forms using
*keyword arguments*. For example, the following login form sends the
``username`` and the ``password`` as form arguments using the POST method::

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

The following code can be used to handle this URL::

    class Root:
        def doLogin(self, username=None, password=None):
            # check the username & password
            ...
        doLogin.exposed = True

Both arguments have to be declared as *keyword arguments*. The default value
can be used either to provide a suitable default value for optional arguments,
or to provide means for the application to detect if some values were missing
from the request.

CherryPy supports both the GET and POST method for HTML forms. Arguments are
passed the same way, regardless of the original method used by the browser to
send data to the web server.

.. _args:

Positional Arguments
^^^^^^^^^^^^^^^^^^^^

.. index:: path, virtual path, path segments, *args, positional arguments

When a request is processed, the URI is split into its components, and each
one is matched in order against the nodes in the tree. Any trailing components
are "virtual path" components and are passed as positional arguments. For
example, the URI ``"/branch/leaf/4"`` might result in
the call: ``app.root.branch.leaf(4)``, or ``app.root.index(branch, leaf, 4)``
depending on how you have your handlers arranged.

Partial matches can happen when a URL contains components that do not map to
the object tree. This can happen for a number of reasons. For example, it may
be an error; the user just typed the wrong URL. But it also can mean that the
URL contains extra arguments.

For example, assume that you have a blog-like application written in CherryPy
that takes the year, month and day as part of the URL
``http://localhost/blog/2005/01/17``. This URL can be handled by the
following code::

    class Root:
        def blog(self, year, month, day):
            ...
        blog.exposed = True
    
    root = Root()

So the URL above will be mapped as a call to::

    root.blog('2005', '1', '17')

In this case, there is a partial match up to the ``blog`` component. The rest
of the URL can't be found in the mounted object tree. In this case, the
``blog()`` method will be called, and the positional parameters will
receive the remaining path segments as arguments. The values are passed as
strings; in the above mentioned example, the arguments would still need to be
converted back into numbers, but the idea is correctly presented.

.. _defaultmethods:

Default methods
^^^^^^^^^^^^^^^

.. index:: default, methods; default

If the default dispatcher is not able to locate a suitable page handler by
walking down the tree, it has a last-ditch option: it starts walking back
''up'' the tree looking for `default` methods. Default methods work just like
any other method with positional arguments, but are defined one level further
down, in case you have multiple methods to expose. For example, we could have
written the above "blog" example equivalently with a "default" method instead::

    class Blog:
        def default(self, year, month, day):
            ...
        default.exposed = True
    
    class Root: pass
    
    root = Root()
    root.blog = Blog()

So the URL ``http://localhost/blog/2005/01/17`` will be mapped as a call to::

    root.blog.default('2005', '1', '17')

You could achieve the same effect by defining a ``__call__`` method in this
case, but "default" just reads better. ;)

Special characters
^^^^^^^^^^^^^^^^^^

You can use dots in a URI like ``/path/to/my.html``, but Python method names
don't allow dots. To work around this, the default dispatcher converts all dots
in the URI to underscores before trying to find the page handler. In the
example, therefore, you would name your page handler "def my_html". However,
this means the page is also available at the URI ``/path/to/my_html``.
If you need to protect the resource (e.g. with authentication), **you must
protect both URLs**.

.. versionadded:: 3.2
   The default dispatcher now takes a 'translate' argument, which converts all
   characters in string.punctuation to underscores using the builtin
   :meth:`str.translate <str.translate>` method of string objects.
   You are free to specify any other translation string of length 256.

Other Dispatchers
-----------------

But Mr. Fielding mentions two kinds of "mapping implementations" above: trees
and hash tables ('dicts' in Python). Some web developers claim trees are
difficult to change as an application evolves, and prefer to use dicts
(or a list of tuples) instead. Under these schemes, the mapping key is often
a regular expression, and the value is the handler function. For example::

    def root_index(name):
        return "Hello, %s!" % name

    def branch_leaf(size):
        return str(int(size) + 3)

    mappings = [
        (r'^/([^/]+)$', root_index),
        (r'^/branch/leaf/(\d+)$', branch_leaf),
        ]

CherryPy allows you to use a :class:`Dispatcher<cherrypy._cpdispatch.Dispatcher>`
other than the default if you wish. By using another
:class:`Dispatcher <cherrypy._cpdispatch.Dispatcher>` (or writing your own),
you gain complete control over the arrangement and behavior of your page
handlers (and config). To use another dispatcher, set the
``request.dispatch`` config entry to the dispatcher you like::

    d = cherrypy.dispatch.RoutesDispatcher()
    d.connect(name='hounslow', route='hounslow', controller=City('Hounslow'))
    d.connect(name='surbiton', route='surbiton', controller=City('Surbiton'),
              action='index', conditions=dict(method=['GET']))
    d.mapper.connect('surbiton', controller='surbiton',
                     action='update', conditions=dict(method=['POST']))

    conf = {'/': {'request.dispatch': d}}
    cherrypy.tree.mount(root=None, config=conf)

A couple of notes about the example above:

* Since Routes has no controller hierarchy, there's nothing to pass as a
  root to :func:`cherrypy.tree.mount <cherrypy._cptree.Tree.mount>`;
  pass ``None`` in this case.
* Usually you'll use the same dispatcher for an entire app, so specifying it
  at the root ("/") is common. But you can use different dispatchers for
  different paths if you like.
* Because the dispatcher is so critical to finding handlers (and their
  ancestors), this is one of the few cases where you *cannot* use
  :ref:`_cp_config <cp_config>`; it's a chicken-and-egg problem:
  you can't ask a handler you haven't found yet how it wants to be found.
* Since Routes are explicit, there's no need to set the ``exposed`` attribute.
  **All routes are always exposed.**

CherryPy ships with additional Dispatchers in :mod:`cherrypy._cpdispatch`.

.. _pagehandlers:

PageHandler Objects
===================

Because the Dispatcher sets
:attr:`cherrypy.request.handler <cherrypy._cprequest.Request.handler>`,
it can also control
the input and output of that handler function by wrapping the actual handler.
The default Dispatcher passes "virtual path" components as positional arguments
and passes query-string and entity (GET and POST) parameters as keyword
arguments. It uses a :class:`PageHandler <cherrypy._cpdispatch.PageHandler>`
object for this, which looks a lot like::

    class PageHandler(object):
        """Callable which sets response.body."""
        
        def __init__(self, callable, *args, **kwargs):
            self.callable = callable
            self.args = args
            self.kwargs = kwargs
        
        def __call__(self):
            return self.callable(*self.args, **self.kwargs)

The actual default PageHandler is a little bit more complicated (because the
args and kwargs are bound later), but you get the idea. And you can see how
easy it would be to provide your own behavior, whether your own inputs or your
own way of modifying the output. Remember, whatever is returned from the
handler will be bound to
:attr:`cherrypy.response.body <cherrypy._cprequest.Response.body>` and will
be used as the response entity.

Replacing page handlers
-----------------------

The handler that's going to be called during a request is available at
:attr:`cherrypy.request.handler <cherrypy._cprequest.Request.handler`,
which means your code has a chance to replace it before the handler runs.
It's a snap to write a Tool to do so with a
:class:`HandlerWrapperTool <cherrypy._cptools.HandlerWrapperTool>`::

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

The default arrangement of CherryPy handlers is a tree. This enables a very
powerful configuration technique: config can be attached to a node in the tree
and cascade down to all children of that node. Since the mapping of URI's to
handlers is not always 1:1, this provides a flexibility which is not as easily
definable in other, flatter arrangements.

However, because the arrangement of config is directly related to the
arrangement of handlers, it is the responsibility of the Dispatcher to collect
per-handler config, merge it with per-URI and global config, and bind the
resulting dict to :attr:`cherrypy.request.config <cherrypy._cprequest.Request.config>`.
This dict is of depth 1 and will contain all config entries which are in
effect for the current request.

