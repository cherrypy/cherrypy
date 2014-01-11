
Custom Response Headers
***********************

Although the ``cherrypy.response.headers`` is usually adequate for
supplying headers in a CherryPy response, it is sometimes desirable for
the server application to customize the order of the resultant headers
or provide multiple headers with duplicate keys. This section describes
how one can accomplish these tasks within the CherryPy framework.

Process
=======

The CherryPy Response object maintains a dictionary of headers until the
finalize phase, after which the headers in the dictionary are converted
into a list of (name, value) tuples. See
``cherrypy._cprequest.Response`` for details.

Therefore, since a dictionary discards order and duplicate keys,
customizing the order or duplicity of keys must occur after the finalize
phase.

This end can be effected using a tool bound to the ``on_end_resource``
hook.

Multiple Headers
================

The following example illustrates the creation of a multiheaders tool to
deliver multiple headers with the same key in the response.

::

    #python
    import cherrypy

    def multi_headers():
        cherrypy.response.header_list.extend(
            cherrypy.response.headers.encode_header_items(
                cherrypy.response.multiheaders))

    cherrypy.tools.multiheaders = cherrypy.Tool('on_end_resource', multi_headers)

    class Root(object):
        @cherrypy.expose
        @cherrypy.tools.multiheaders()
        def index(self):
            cherrypy.response.multiheaders = [('foo', '1'), ('foo', '2')]
            return "Hello"

    cherrypy.quickstart(Root())

Header Order
============

The following example illustrates the creation of a firstheaders tool to
deliver headers in a specified order (at the beginning) in the response.

::

    #python
    import cherrypy

    def first_headers():
        cherrypy.response.header_list[:0] = cherrypy.response.first_headers

    cherrypy.tools.firstheaders = cherrypy.Tool('on_end_resource', first_headers)

    class Root(object):
        @cherrypy.expose
        @cherrypy.tools.firstheaders()
        def index(self):
            cherrypy.response.first_headers = [('foo', '1'), ('foo', '2')]
            return "Hello"

    cherrypy.quickstart(Root())
