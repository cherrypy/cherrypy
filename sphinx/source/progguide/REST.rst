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

 - "resources" are concepual objects represented by the system - any
   information that can be named is a resource.
 - "state" is data held by or associated with resources
 - "representations" are information in state with a specific encoding
 - "methods" are invoked to transfer or mutate state.
 - an "identifier" is a URL or URI which uniquely and usually globally
   references a resource.

More information on REST can be found in abundance in Wikipedia and
other readily-available resources.

Implementing REST in CherryPy
=============================

From the canonical `Roy Fielding dissertation <http://www.ics.uci.edu/~fielding/pubs/dissertation/rest_arch_style.htm#sec_5_1_5>`_ :

    REST is defined by four interface constraints: identification of resources;
    manipulation of resources through representations; self-descriptive messages;
    and, hypermedia as the engine of application state

This section covers each of these four contstraints and demonstrates how each
is applied in a CherryPy implementation.

Identification of Resources
---------------------------

As an HTTP service provider, resources represented in CherryPy are
referenced by HTTP URIs (Uniform Resource Identifiers). A URI consists
of four parts: scheme, hierarchical identifier, query, and fragment.
For HTTP, the scheme is always ``http`` or ``https``. The hierarchical
identifier consists of an authority (typically host/port) and a path
(similar to a file system path, but not necessarily representing an
actual path).

A single CherryPy instance is typically bound to a single
server/port pair, such that the scheme://authority portion of the URI
references the server. This aspect is configured through the
``server.socket_host`` and ``server.socket_port`` options or via another
hosting server.

Within the CherryPy server, the remainder of the hierarchical
identifier--the path--is mapped to Python objects
via the Dispatch mechanism. This behavior is highly
customizable and documented in :doc:`/intro/concepts/dispatching`.

Using the default dispatcher and page handlers, the path of the URI
maps to a hierarchy of Python identifiers in the CherryPy app. For
example, the URI path ``/container/objects/pencil`` will result in a
call to ``app.root.container.objects.pencil()`` where ``app`` is the
CherryPy app.

Manipulation of Resources Through Representations
-------------------------------------------------

REST defines the use of the HTTP protocol and HTTP methods to implement
the standard REST methods.

 - GET retrieves the state of a specific resource,
 - PUT creates or replaces the state of a specific resource,
 - POST passes information to a resource to use at it sees fit,
 - DELETE removes resources.

The default dispatcher in CherryPy stores the HTTP method name at
:attr:`cherrypy.request.method<cherrypy._cprequest.Request.method>`.

Because HTTP defines these invocation methods, the most direct
way to implement REST using CherryPy is to utilize the
:class:`MethodDispatcher<cherrypy._cpdispatch.MethodDispatcher>`
instead of the default dispatcher. To enable
the method dispatcher, add the
following to your configuration for the root URI ("/")::

        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
        }

Now, the REST methods will map directly to the same method names on
your resources. That is, a GET method on a CherryPy class implements
the HTTP GET on the resource represented by that class.

For example::

    class Resource(object):
        
        exposed = True
        
        def GET(self):
            return """Some representation of self"""
        
        def PUT(self):
            self.content = initialize_from_representation(cherrypy.request.body.read())

The concrete implementation of GET and PUT has been omitted, but the
basic concepts remain: GET returns some meaningful representation of
the resource and PUT stores an instance of an object represented by the
content in the body of the request.

Self-Descriptive Messages
-------------------------

REST enables powerful clients and intermediaries by requiring messages to be
self-descriptive; that is, everything you need to know about a message is
carried within the message itself, either in headers or within the definition
of the message's declared media type.

CherryPy gives you easy access to the headers. It's as simple as
:attr:`cherrypy.request.headers<cherrypy._cprequest.Request.headers>` and
:attr:`cherrypy.response.headers<cherrypy._cprequest.Response.headers>`!
Each is a normal Python dictionary which you can read and write as you like.
They also have additional functions to help you parse complex values according
to the HTTP spec.

CherryPy also allows you to set whatever response Content-Type you prefer,
just like any other response header. You have complete control. When reading
request entities, you can register :ref:`custombodyprocessors` for different
media types.

Hypermedia as the Engine of Application State
---------------------------------------------

REST is designed as a stateless protocol--all application state is
maintained with the application at the client. Thus, concepts such as a
"session" need not be maintained by the server. CherryPy does not enable
sessions by default, so it is well-suited to the RESTful style.

In order for the client to maintain meaningful state, however, the REST
server implementer must provide meaningful URIs which supply semantic
links between resources.

For example, a CherryPy application might have a resource index, which
a client might retrieve to inspect the application for other resources::

    class ResourceIndex(object):
        def GET(self):
            items = [item.get_href() for item in self.get_all_items()]
            return ', '.join(items)

This very simple example demonstrates how to create an index of
comma-separated hypertext references. This example assumes the client
can effectively interpret comma-separated references. In practice,
another representation such as HTML or JSON might be used.

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
directly::

    import cherrypy

    class Resource(object):
        
        def __init__(self, content):
            self.content = content
        
        exposed = True
        
        def GET(self):
            return self.to_html()
        
        def PUT(self):
            self.content = self.from_html(cherrypy.request.body.read())

        def to_html(self):
            html_item = lambda (name,value): '<div>{name}:{value}</div>'.format(\*\*vars())
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
            html_item = lambda (name,value): '<div><a href="{value}">{name}</a></div>'.format(\*\*vars())
            items = map(html_item, self.content.items())
            items = ''.join(items)
            return '<html>{items}</html>'.format(**vars())

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
