"""Native adapter for serving CherryPy via mod_python"""

from mod_python import apache
import cherrypy


def setup(req):
    # Run any setup function defined by a "PythonOption cherrypy.setup" directive.
    options = req.get_options()
    if 'cherrypy.setup' in options:
        modname, fname = options['cherrypy.setup'].split('::')
        mod = __import__(modname, globals(), locals(), [fname])
        func = getattr(mod, fname)
        func()
    
    cherrypy.config.update({'global' : {'server.log_to_screen' : False}})
    
    if cherrypy.engine.state == cherrypy._cpengine.STOPPED:
        cherrypy.engine.start(blocking=False)
    elif cherrypy.engine.state == cherrypy._cpengine.STARTING:
        cherrypy.engine.wait()
    
    def cherrypy_cleanup(data):
        cherrypy.engine.stop()
    try:
        # apache.register_cleanup wasn't available until 3.1.4.
        apache.register_cleanup(cherrypy_cleanup)
    except AttributeError:
        req.server.register_cleanup(req, cherrypy_cleanup)


class _ReadOnlyRequest:
    expose = ('read', 'readline', 'readlines')
    def __init__(self, req):
        for method in self.expose:
            self.__dict__[method] = getattr(req, method)


_isSetUp = False
def handler(req):
    try:
        global _isSetUp
        if not _isSetUp:
            setup(req)
            _isSetUp = True
        
        # Obtain a Request object from CherryPy
        clientAddress = req.connection.remote_addr
        remoteHost = clientAddress[0]
        scheme = req.parsed_uri[0] or 'http'
        request = cherrypy.engine.request(clientAddress, remoteHost, scheme)
        req.get_basic_auth_pw()
        request.login = req.user
        # apache.mpm_query only became available in mod_python 3.1
        request.multithread = bool(apache.mpm_query(apache.AP_MPMQ_IS_THREADED))
        request.multiprocess = bool(apache.mpm_query(apache.AP_MPMQ_IS_FORKED))
        
        # Run the CherryPy Request object and obtain the response
        requestLine = req.the_request
        headers = req.headers_in.items()
        rfile = _ReadOnlyRequest(req)
        response = request.run(requestLine, headers, rfile)
        
        sendResponse(req, response)
        request.close()
    except:
        cherrypy.log(traceback=True)
    return apache.OK

def sendResponse(req, response):
    # Set response status
    req.status = int(response.status[:3])
    
    # Set response headers
    req.content_type = "text/plain"
    for header, value in response.header_list:
        if header.lower() == 'content-type':
            req.content_type = value
            continue
        req.headers_out.add(header, value)
    
    # Cookie
    cook_out = response.simple_cookie.output()
    if cook_out:
        for line in cook_out.split('\n'):
            req.headers_out.add(*tuple(v.strip() for v in line.split(':', 1)))
    
    # Set response body
    if isinstance(response.body, basestring):
        req.write(response.body)
    else:
        for seg in response.body:
            req.write(seg)
