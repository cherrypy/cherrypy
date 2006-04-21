import sys
import xmlrpclib

import cherrypy
from cherrypy import _cprequest


def process_body():
    request = cherrypy.request
    
    cl = int(request.headers.get('Content-Length') or 0)
    data = request.rfile.read(cl)
    try:
        params, method = xmlrpclib.loads(data)
    except Exception:
        params, method = ('ERROR PARAMS', ), 'ERRORMETHOD'
    request.rpcMethod, request.rpcParams = method, params
    
    # patch the path. there are only a few options:
    # - 'RPC2' + method >> method
    # - 'someurl' + method >> someurl.method
    # - 'someurl/someother' + method >> someurl.someother.method
    if not request.object_path.endswith('/'):
        request.object_path += '/'
    if request.object_path.startswith('/RPC2/'):
        # strip the first /rpc2
        request.object_path = request.object_path[5:]
    request.object_path += str(method).replace('.', '/')
    request.paramList = list(params)
    request.processRequestBody = False

def main(encoding='utf-8', allow_none=0):
    """Obtain and set cherrypy.response.body from a page handler.
    
    Python's None value cannot be used in standard XML-RPC; to allow
    using it via an extension, provide a true value for allow_none.
    """
    dispatch = cherrypy.config.get("dispatcher") or _cprequest.Dispatcher()
    handler = dispatch(path)
    request = cherrypy.request
    body = handler(*(request.virtual_path + request.paramList),
                   **request.params)
    respond(xmlrpclib.dumps((body,), methodresponse=1,
                            encoding=encoding, allow_none=allow_none))
    return True

def error_response():
    body = str(sys.exc_info()[1])
    respond(xmlrpclib.dumps(xmlrpclib.Fault(1, body)))

def respond(body):
    # The XML-RPC spec (http://www.xmlrpc.com/spec) says:
    # "Unless there's a lower-level error, always return 200 OK."
    # Since Python's xmlrpclib interprets a non-200 response
    # as a "Protocol Error", we'll just return 200 every time.
    response = cherrypy.response
    response.status = '200 OK'
    response.body = body
    response.headers['Content-Type'] = 'text/xml'
    response.headers['Content-Length'] = len(body)

def setup(conf):
    """Hook this tool into cherrypy.request using the given conf."""
    cherrypy.request.hooks.attach('before_process_body', process_body, conf)
    cherrypy.request.hooks.attach_main(main, conf)
    cherrypy.request.hooks.attach('after_error_response', error_response, conf)
