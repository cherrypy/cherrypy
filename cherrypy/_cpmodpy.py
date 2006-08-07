"""Native adapter for serving CherryPy via mod_python"""

from mod_python import apache
import cherrypy
from cherrypy._cperror import format_exc, bare_error


def setup(req):
    # Run any setup function defined by a "PythonOption cherrypy.setup" directive.
    options = req.get_options()
    if 'cherrypy.setup' in options:
        modname, fname = options['cherrypy.setup'].split('::')
        mod = __import__(modname, globals(), locals(), [fname])
        func = getattr(mod, fname)
        func()
    
    cherrypy.config.update({'global' : {'log_to_screen' : False}})
    
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
        
        try:
            # apache.mpm_query only became available in mod_python 3.1
            q = apache.mpm_query
            threaded = q(apache.AP_MPMQ_IS_THREADED)
            forked = q(apache.AP_MPMQ_IS_FORKED)
        except AttributeError:
            bad_value = ("You must provide a PythonOption '%s', "
                         "either 'on' or 'off', when running a version "
                         "of mod_python < 3.1")
            
            threaded = options.get('multithread', '').lower()
            if threaded == 'on':
                threaded = True
            elif threaded == 'off':
                threaded = False
            else:
                raise ValueError(bad_value % "multithread")
            
            forked = options.get('multiprocess', '').lower()
            if forked == 'on':
                forked = True
            elif forked == 'off':
                forked = False
            else:
                raise ValueError(bad_value % "multiprocess")
        request.multithread = bool(threaded)
        request.multiprocess = bool(forked)
        
        # Run the CherryPy Request object and obtain the response
        headers = req.headers_in.items()
        rfile = _ReadOnlyRequest(req)
        response = request.run(req.method, req.uri, req.args or "",
                               req.protocol, headers, rfile)
        
        sendResponse(req, response.status, response.header_list, response.body)
        request.close()
    except:
        tb = format_exc()
        cherrypy.log(tb)
        s, h, b = bare_error()
        sendResponse(req, s, h, b)
    return apache.OK

def sendResponse(req, status, headers, body):
    # Set response status
    req.status = int(status[:3])
    
    # Set response headers
    req.content_type = "text/plain"
    for header, value in headers:
        if header.lower() == 'content-type':
            req.content_type = value
            continue
        req.headers_out.add(header, value)
    
    # Set response body
    if isinstance(body, basestring):
        req.write(body)
    else:
        for seg in body:
            req.write(seg)

