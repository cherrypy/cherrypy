import sys
import xmlrpclib

import cherrypy


def process_body():
    """Return (params, method) from request body."""
    try:
        return xmlrpclib.loads(cherrypy.request.body.read())
    except Exception:
        return ('ERROR PARAMS', ), 'ERRORMETHOD'


def patched_path(path, method):
    """Return 'path' with the rpcMethod appended."""
    if not path.endswith('/'):
        path += '/'
    if path.startswith('/RPC2/'):
        # strip the first /rpc2
        path = path[5:]
    path += str(method).replace('.', '/')
    return path


def _set_response(body):
    # The XML-RPC spec (http://www.xmlrpc.com/spec) says:
    # "Unless there's a lower-level error, always return 200 OK."
    # Since Python's xmlrpclib interprets a non-200 response
    # as a "Protocol Error", we'll just return 200 every time.
    response = cherrypy.response
    response.status = '200 OK'
    response.body = body
    response.headers['Content-Type'] = 'text/xml'
    response.headers['Content-Length'] = len(body)


def respond(body, encoding='utf-8', allow_none=0):
    _set_response(xmlrpclib.dumps((body,), methodresponse=1,
                                  encoding=encoding,
                                  allow_none=allow_none))

def wrap_error():
    body = str(sys.exc_info()[1])
    _set_response(xmlrpclib.dumps(xmlrpclib.Fault(1, body)))

