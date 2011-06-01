import sys

import cherrypy
from cherrypy._cpcompat import ntob

def process_body():
    """Return (params, method) from request body."""
    try:
        # Python 3
        from xmlrpc.client import loads
    except ImportError:
        # Python 2
        from xmlrpclib import loads
    
    try:
        return loads(cherrypy.request.body.read())
    except Exception:
        return ('ERROR PARAMS', ), 'ERRORMETHOD'


def patched_path(path):
    """Return 'path', doctored for RPC."""
    if not path.endswith('/'):
        path += '/'
    if path.startswith('/RPC2/'):
        # strip the first /rpc2
        path = path[5:]
    return path


def _set_response(body):
    # The XML-RPC spec (http://www.xmlrpc.com/spec) says:
    # "Unless there's a lower-level error, always return 200 OK."
    # Since Python's xmlrpclib interprets a non-200 response
    # as a "Protocol Error", we'll just return 200 every time.
    response = cherrypy.response
    response.status = '200 OK'
    response.body = ntob(body, 'utf-8')
    response.headers['Content-Type'] = 'text/xml'
    response.headers['Content-Length'] = len(body)


def respond(body, encoding='utf-8', allow_none=0):
    try:
        # Python 2
        from xmlrpclib import Fault, dumps
    except ImportError:
        # Python 3
        from xmlrpc.client import Fault, dumps
    if not isinstance(body, Fault):
        body = (body,)
    _set_response(dumps(body, methodresponse=1,
                        encoding=encoding,
                        allow_none=allow_none))

def on_error(*args, **kwargs):
    body = str(sys.exc_info()[1])
    try:
        # Python 2
        from xmlrpclib import Fault, dumps
    except ImportError:
        # Python 3
        from xmlrpc.client import Fault, dumps
    _set_response(dumps(Fault(1, body)))

