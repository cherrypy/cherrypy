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

    class Root(object):
        def index(self):
	    """Handle the / URI"""
        index.exposed = True


or use a decorator::

    class Root(object):
        @cherrypy.expose
        def index(self):
	    """Handle the / URI"""


When it is a special method, such as ``__call__``, that is to be invoked,
the exposed attribute must be set on the class itself::

    class Node(object):
        exposed = True
        def __call__(self):
            """ """

The techniques can be mixed, for example::

    """This example can handle the URIs:
    /       ->  Root.index
    /page   ->  Root.page
    /node   ->  Node.__call__
    """
    import cherrypy


    class Node(object):
        exposed = True
    
        def __call__(self):
	    return "The node content"


    class Root(object):

        def __init__(self):
	    self.node = Node()

        @cherrypy.expose       
        def index(self):
            return "The index of the root object"

        def page(self):
            return 'This is the "page" content'
        page.exposed = True
    

    if __name__ == '__main__':
        cherrypy.quickstart(Root())
       
