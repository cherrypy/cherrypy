"""a WSGI application filter for CherryPy"""

# by Christian Wyglendowski

import sys

import cherrypy
from cherrypy.filters.basefilter import BaseFilter
from cherrypy.lib import cptools
from cherrypy._cputil import get_object_trail


class NoWSGIEnvironmentError(Exception):
    pass


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
    
    for compatibility with the 2.2beta release of CP
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
    environ["SERVER_PORT"] = cherrypy.config.get('server.socketPort')
    environ["REMOTE_HOST"] = cherrypy.request.remoteHost
    environ["REMOTE_ADDR"] = cherrypy.request.remoteAddr
    environ["REMOTE_PORT"] = cherrypy.request.remotePort
    # then all the http headers
    headers = cherrypy.request.headers
    environ["CONTENT_TYPE"] = headers.get("Content-type", "")
    environ["CONTENT_LENGTH"] = headers.get("Content-length", "")
    for (k, v) in headers.iteritems():
        envname = "HTTP_" + k.upper().replace("-","_")
        environ[envname] = v
    return environ


class WSGIAppFilter(BaseFilter):
    """A filter for running any WSGI middleware/application within CP.

    It can be used through the config system or by adding it to
    a classes _cp_filters special attribute.  Here are the parameters:

    wsgi_app (wsgiapp_filter.app) - any wsgi application callable
    env_update (wsgiapp_filter.env_update) - a dictionary with
    arbitrary keys and values to be merged with the WSGI
    environment dictionary.

    Examples:

    # using _cp_filters
    class Whatever:
        _cp_filters = [WSGIAppFilter(some_app)]

    # using a config file
    [/hosted/app]
    wsgiapp_filter.on = True
    wsgiapp_filter.app = 'package.module.wsgi_app_callable'
    wsgiapp_filter.env_update = {'running_in_cp':True}
    """

    def __init__(self, wsgi_app=None, env_update=None):
        self.app = wsgi_app
        self.env_update = env_update or {}
   
    def before_request_body(self):
        request = cherrypy.request
        enabled = cherrypy.config.get('wsgiapp_filter.on', False)
        request.wsgi_app = self.app
        request.wsgi_env_update = self.env_update
        request.wsgiapp_filter_on = enabled or bool(self.app)

        if not request.wsgiapp_filter_on:
            return

        if not request.wsgi_app:
            app = cherrypy.config.get('wsgiapp_filter.app', None)
            if app and isinstance(app, basestring):
                app = cptools.attributes(app)
            request.wsgi_app = app
        
        if not request.wsgi_env_update:
            env_update = cherrypy.config.get('wsgiapp_filter.env_update', {})
            request.wsgi_env_update = env_update

        # keep the request body intact so the wsgi app
        # can have its way with it
        cherrypy.request.processRequestBody = False

    def before_main(self):
        """run the wsgi_app and set response.body to its output
        """
        
        request = cherrypy.request

        if not request.wsgiapp_filter_on:
            return
        
        # if the static filter is on for this path and
        # request.execute_main is False, assume that the
        # static filter has already taken care of this request
        staticfilter_on = cherrypy.config.get('static_filter.on', False)
        if staticfilter_on and not request.execute_main:
            return

        try:
            environ = request.wsgi_environ
            sn, pi = get_path_components(request.path)
            environ['SCRIPT_NAME'] = sn
            environ['PATH_INFO'] = pi
        except AttributeError:
            environ = make_environ()

        # update the environ with the dict passed to the filter's
        # constructor
        environ.update(request.wsgi_env_update)

        # run the wsgi app and have it set response.body
        cherrypy.response.body = request.wsgi_app(environ, start_response)
        
        # tell CP not to handle the request further
        request.execute_main = False


class WSGIApp(object):
    """a convenience class used to easily mount a wsgi app.

    example:
    cherrypy.root = SomeRoot()
    cherrypy.root.otherapp = WSGIApp(other_wsgi_app)
    """
    def __init__(self, app, env_update=None):
        self._cpFilterList = [WSGIAppFilter(app, env_update)]


if __name__ == '__main__':

    def my_app(environ, start_response):
        status = '200 OK'
        response_headers = [('Content-type', 'text/plain')]
        start_response(status, response_headers)
        yield 'Hello, world!\n'
        yield 'This is a wsgi app running within CherryPy!\n\n'
        keys = environ.keys()
        keys.sort()
        for k in keys:
            yield '%s: %s\n' % (k,environ[k])

    class Root(object):
        @cherrypy.expose
        def index(self):
            yield "<h1>Hi, from CherryPy!</h1>"
            yield "<a href='app'>A non-CP WSGI app</a><br>"
            yield "<br>"
            yield "SCRIPT_NAME and PATH_INFO get set "
            yield "<a href='app/this/n/that'>properly</a>"

    # mount standard CherryPy app
    cherrypy.root = Root()
    # mount the WSGI app
    cherrypy.root.app = WSGIApp(my_app, {'cherrypy.wsgi_filter':True})


    cherrypy.server.start()
        

