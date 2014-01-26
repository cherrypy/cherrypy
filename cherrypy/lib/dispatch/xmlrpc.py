from cherrypy.lib.dispatch.object import Dispatcher
from cherrypy.lib.tools import xmlrpcutil


def XMLRPCDispatcher(next_dispatcher=Dispatcher()):
    def xmlrpc_dispatch(path_info):
        path_info = xmlrpcutil.patched_path(path_info)
        return next_dispatcher(path_info)
    return xmlrpc_dispatch
