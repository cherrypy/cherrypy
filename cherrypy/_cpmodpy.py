"""Native adapter for serving CherryPy via mod_python"""

import cherrypy
from cherrypy._cperror import format_exc, bare_error
from cherrypy.lib import http



# ------------------------------ Request-handling


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
        from mod_python import apache
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
    from mod_python import apache
    try:
        global _isSetUp
        if not _isSetUp:
            setup(req)
            _isSetUp = True
        
        # Obtain a Request object from CherryPy
        local = req.connection.local_addr
        local = http.Host(local[0], local[1], req.connection.local_host or "")
        remote = req.connection.remote_addr
        remote = http.Host(remote[0], remote[1], req.connection.remote_host or "")
        
        scheme = req.parsed_uri[0] or 'http'
        request = cherrypy.engine.request(local, remote, scheme)
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
        
        sn = cherrypy.tree.script_name(req.uri or "/")
        if sn is None:
            send_response(req, '404 Not Found', [], '')
        else:
            request.app = cherrypy.tree.apps[sn]
            
            # Run the CherryPy Request object and obtain the response
            headers = req.headers_in.items()
            rfile = _ReadOnlyRequest(req)
            response = request.run(req.method, req.uri, req.args or "",
                                   req.protocol, headers, rfile)
            
            send_response(req, response.status, response.header_list, response.body)
            request.close()
    except:
        tb = format_exc()
        cherrypy.log(tb)
        s, h, b = bare_error()
        send_response(req, s, h, b)
    return apache.OK

def send_response(req, status, headers, body):
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



# --------------- Startup tools for CherryPy + mod_python --------------- #


import os
import re


def read_process(cmd, args=""):
    pipein, pipeout = os.popen4("%s %s" % (cmd, args))
    try:
        firstline = pipeout.readline()
        if (re.search(r"(not recognized|No such file|not found)", firstline,
                      re.IGNORECASE)):
            raise IOError('%s must be on your system path.' % cmd)
        output = firstline + pipeout.read()
    finally:
        pipeout.close()
    return output


class ModPythonServer(object):
    
    template = """
# Apache2 server configuration file for running CherryPy with mod_python.

DocumentRoot "/"
Listen %(port)s
LoadModule python_module modules/mod_python.so

<Location %(loc)s>
    SetHandler python-program
    PythonHandler %(handler)s
    PythonDebug On
%(opts)s
</Location>
"""
    
    def __init__(self, loc="/", port=80, opts=None, apache_path="apache",
                 handler="cherrypy._cpmodpy::handler"):
        self.loc = loc
        self.port = port
        self.opts = opts
        self.apache_path = apache_path
        self.handler = handler
    
    def start(self):
        opts = "".join(["    PythonOption %s %s\n" % (k, v)
                        for k, v in self.opts])
        conf_data = self.template % {"port": self.port,
                                     "loc": self.loc,
                                     "opts": opts,
                                     "handler": self.handler,
                                     }
        
        mpconf = os.path.join(os.path.dirname(__file__), "cpmodpy.conf")
        f = open(mpconf, 'wb')
        try:
            f.write(conf_data)
        finally:
            f.close()
        
        response = read_process(self.apache_path, "-k start -f %s" % mpconf)
        self.ready = True
        return response
    
    def stop(self):
        os.popen("apache -k stop")
        self.ready = False

