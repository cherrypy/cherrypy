"""a WSGI application tool for CherryPy"""

import sys

import cherrypy


# is this sufficient for start_response?
def start_response(status, response_headers, exc_info=None):
    cherrypy.response.status = status
    headers_dict = dict(response_headers)
    cherrypy.response.headers.update(headers_dict)

def make_environ():
    """grabbed some of below from _cpwsgiserver.py
    
    for hosting WSGI apps in non-WSGI environments (yikes!)
    """
    
    # create and populate the wsgi environment
    environ = dict()
    environ["wsgi.version"] = (1,0)
    environ["wsgi.url_scheme"] = cherrypy.request.scheme
    environ["wsgi.input"] = cherrypy.request.rfile
    environ["wsgi.errors"] = sys.stderr
    environ["wsgi.multithread"] = True
    environ["wsgi.multiprocess"] = False
    environ["wsgi.run_once"] = False
    environ["REQUEST_METHOD"] = cherrypy.request.method
    environ["SCRIPT_NAME"] = cherrypy.request.script_name
    environ["PATH_INFO"] = cherrypy.request.path_info
    environ["QUERY_STRING"] = cherrypy.request.query_string
    environ["SERVER_PROTOCOL"] = cherrypy.request.protocol
    server_name = getattr(cherrypy.server.httpserver, 'server_name', "None")
    environ["SERVER_NAME"] = server_name 
    environ["SERVER_PORT"] = cherrypy.config.get('server.socket_port')
    environ["REMOTE_HOST"] = cherrypy.request.remote_host
    environ["REMOTE_ADDR"] = cherrypy.request.remote_addr
    environ["REMOTE_PORT"] = cherrypy.request.remote_port
    # then all the http headers
    headers = cherrypy.request.headers
    environ["CONTENT_TYPE"] = headers.get("Content-type", "")
    environ["CONTENT_LENGTH"] = headers.get("Content-length", "")
    for (k, v) in headers.iteritems():
        envname = "HTTP_" + k.upper().replace("-","_")
        environ[envname] = v
    return environ


def run(app, env=None):
    """Run the (WSGI) app and set response.body to its output"""
    try:
        environ = cherrypy.request.wsgi_environ
    except AttributeError:
        environ = make_environ()
    environ['SCRIPT_NAME'] = cherrypy.request.script_name
    environ['PATH_INFO'] = cherrypy.request.path_info
    
    if env:
        environ.update(env)
    
    # run the wsgi app and have it set response.body
    cherrypy.response.body = app(environ, start_response)
    
    return True

