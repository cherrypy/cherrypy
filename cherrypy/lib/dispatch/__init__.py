"""CherryPy dispatchers.

A 'dispatcher' is the object which looks up the 'page handler' callable
and collects config for the current request based on the path_info, other
request attributes, and the application architecture. The core calls the
dispatcher as early as possible, passing it a 'path_info' argument.

The default dispatcher discovers the page handler by matching path_info
to a hierarchical arrangement of objects, starting at request.app.root.
"""

# For compatibility. Consider removing in CP4 final.
from cherrypy.lib.dispatch.method import MethodDispatcher
from cherrypy.lib.dispatch.object import Dispatcher
from cherrypy.lib.dispatch.route import RoutesDispatcher
from cherrypy.lib.dispatch.virtualhost import VirtualHost
from cherrypy.lib.dispatch.xmlrpc import XMLRPCDispatcher
