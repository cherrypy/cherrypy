********
Exposing
********

Any object that is attached to the root object is traversible via the internal
URL-to-object mapping routine. However, it does not mean that the object itself
is directly accessible via the Web. For this to happen, the object has to be
**exposed**.

Exposing objects
----------------

CherryPy maps URL requests to objects and invokes the suitable callable
automatically. The callables that can be invoked as a result of external
requests are said to be **exposed**.

Objects are **exposed** in CherryPy by setting the ``exposed`` attribute.
Most often, a method on an object is the callable that is to be invoked. In
this case, one can directly set the exposed attribute::

    class Root:
        def index(self):
            ...
        index.exposed = True


or use a decorator::

        @cherrypy.expose
        def index(self):
            ...


When it is a special method, such as ``__call__``, that is to be invoked,
the exposed attribute must be set on the class itself::

    class Node:
        exposed = True
        def __call__(self):
            ...


