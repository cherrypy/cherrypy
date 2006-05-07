"""a WSGI application tool for CherryPy"""

import sys

import cherrypy
from cherrypy import _cphttptools
from cherrypy._cputil import get_object_trail


# is this sufficient for start_response?
def start_response(status, response_headers, exc_info=None):
    cherrypy.response.status = status
    headers_dict = dict(response_headers)
    cherrypy.response.headers.update(headers_dict)

def get_path_components(path):
    """returns (script_name, path_info)

    determines what part of the path belongs to cp (script_name)
    and what part belongs to the wsgi application (path_info)
    """
    no_parts = ['']
    object_trail = get_object_trail(path)
    root = object_trail.pop(0)
    if not path.endswith('/index'):
        object_trail.pop()
    script_name_parts = [""]
    path_info_parts = [""]
    for (pc,obj) in object_trail:
        if obj:
            script_name_parts.append(pc)
        else:
            path_info_parts.append(pc)
    script_name = "/".join(script_name_parts)
    path_info = "/".join(path_info_parts)
    if len(script_name) > 1 and path.endswith('/'):
        path_info = path_info + '/'
    
    if script_name and not script_name.startswith('/'):
        script_name = '/' + script_name
    if path_info and not path_info.startswith('/'):
        path_info = '/' + path_info
    
    return script_name, path_info

def make_environ():
    """grabbed some of below from _cpwsgiserver.py
    
    for hosting WSGI apps in non-WSGI environments (yikes!)
    """

    script_name, path_info = get_path_components(cherrypy.request.path)
    
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
    environ["SCRIPT_NAME"] = script_name
    environ["PATH_INFO"] = path_info
    environ["QUERY_STRING"] = cherrypy.request.queryString
    environ["SERVER_PROTOCOL"] = cherrypy.request.version
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


def WSGIAppRequestFactory(wsgi_app, env_update=None):
    """
    wsgi_app - any wsgi application callable
    env_update - a dictionary with arbitrary keys and values to be 
                 merged with the WSGI environment dictionary.
    """
    
    class WSGIAppRequest(_cphttptools.Request):
        """A custom Request object for running a WSGI app within CP."""
       
        def process_body(self):
            pass
        
        def main(self, *args, **kwargs):
            """run the wsgi_app and set response.body to its output"""
            try:
                env = self.wsgi_environ
                env['SCRIPT_NAME'], env['PATH_INFO'] = get_path_components(self.path)
            except AttributeError:
                env = make_environ()
            env.update(env_update or {})
            cherrypy.response.body = wsgi_app(env, start_response)
    return WSGIAppRequest
