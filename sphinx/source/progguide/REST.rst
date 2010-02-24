*****************************************
Creating RESTful applications in CherryPy
*****************************************

Introduction
============

REST (Representational State Transfer) is an architectural style that
is well-suited to implementation in CherryPy. Both REST and CherryPy
heavily leverage the HTTP protocol but otherwise carry minimal
requisite overhead. This chapter briefly discusses the purpose of
REST and an example implementation in CherryPy.

REST in a nutshell
==================

The REST architectural style describes how domain models and their state
are referenced and transferred. The primary goal of REST is promote
certain advantageous qualities of a distributed system, namely high
visibility, scalability, extensibility.

Terminology
-----------

 - "resources" are concepual objects represented by the system.
 - "state" is data held by or associated with resources
 - "representations" are information in state with a specific encoding
 - "methods" are invoked to transfer or mutate state.
 - an "identifier" is a URL or URI which uniquely and usually globally
   references a resource.

REST defines the use of the HTTP protocol and HTTP methods to implement
the standard REST methods.

 - GET retrieves the state of a specific resource,
 - PUT creates or replaces the state of a specific resource,
 - POST passes information to a resource to use at it sees fit,
 - DELETE removes resources.

More information on REST can be found in abundance in Wikipedia and
other readily-available resources.

Implementing REST in CherryPy
=============================

From the canonical `Roy Fielding dissertation <http://www.ics.uci.edu/~fielding/pubs/dissertation/rest_arch_style.htm#sec_5_1_5>`_ :

    REST is defined by four interface constraints: identification of resources; manipulation of resources through representations; self-descriptive messages; and, hypermedia as the engine of application state

.. TODO: Cover each of the four constraints and demonstrate how they are
   apply in a CherryPy implementation.

Since HTTP defines a number of invocation methods, the most direct
way to implement REST using CherryPy is to utilize the
:class:`MethodDispatcher`. To enable the method dispatcher, add the
following to your config file::

    [/]
    request.dispatch: cherrypy.dispatch.MethodDispatcher()

Now, the REST methods will map directly to the same method names on
your resources. That is, a GET method on a CherryPy class implements
the HTTP GET on the resource represented by that class.

A Quick Example
===============

For example, consider the following contrived REST+HTML specification.

1. Resources store arbitrary key/value pairs with unique keys
   (represented as a Python dict).

2. A GET request returns colon-separated key/value pairs in ``<div>``
   elements.

3. A PUT request accepts colon-separated key/value pairs in ``<div>``
   elements.

4. An index resource provides an HTML anchor tag (hypertext link) to objects
   which it indexes (where the keys represent the names and the values
   represent the link).

A REST+HTML implementation was chosen for this example as HTML defines
relative links, which keeps the example simple yet functional.

Complete Example
----------------

Brining the above code samples together and adding some basic
configuration results in the following program, which can be run
directly.

    class Resource(object):
        
        def __init__(self, content):
            self.content = content
        
        exposed = True
        
        def GET(self):
            return self.to_html()
        
        def PUT(self):
            self.content = self.from_html(cherrypy.request.body.read())

        def to_html(self):
            html_item = lambda (name,value): '<div>{name}:{value}</div>'.format(**vars())
            items = map(html_item, self.content.items())
            items = ''.join(items)
            return '<html>{items}</html>'.format(**vars())

        @staticmethod
        def from_html(data):
            pattern = re.compile(r'\<div\>(?P<name>.*?)\:(?P<value>.*?)\</div\>')
            items = [match.groups() for match in pattern.finditer(data)]
            return dict(items)

    class ResourceIndex(Resource):
        def to_html(self):
            html_item = lambda (name,value): '<div><a href="{value}">{name}</a></div>'.format(**vars())
            items = map(html_item, self.content.items())
            items = ''.join(items)
            return '<html>{items}</html>'.format(**vars())

    import cherrypy

    class Root(object):
        pass

    root = Root()

    root.sidewinder = Resource({'color': 'red', 'weight': 176, 'type': 'stable'})
    root.teebird = Resource({'color': 'green', 'weight': 173, 'type': 'overstable'})
    root.blowfly = Resource({'color': 'purple', 'weight': 169, 'type': 'putter'})
    root.resource_index = ResourceIndex({'sidewinder': 'sidewinder', 'teebird': 'teebird', 'blowfly': 'blowfly'})

    conf = {
        'global': {
            'server.socket_host': '0.0.0.0',
            'server.socket_port': 8000,
        },
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
        }
    }

    cherrypy.quickstart(root, '/', conf)

Conclusion
==========

CherryPy provides a straightforward interface for readily creating
RESTful interfaces.
