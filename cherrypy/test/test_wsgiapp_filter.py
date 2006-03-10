import test
test.prefer_parent_path()

import cherrypy
from cherrypy.filters.wsgiappfilter import WSGIAppFilter, WSGIApp

def test_app(environ, start_response):
    status = '200 OK'
    response_headers = [('Content-type', 'text/plain')]
    start_response(status, response_headers)
    yield 'Hello, world!\n'
    yield 'This is a wsgi app running within CherryPy!\n\n'
    keys = environ.keys()
    keys.sort()
    for k in keys:
        yield '%s: %s\n' % (k,environ[k])

class Root:
    def index(self):
        return "I'm a regular CherryPy page handler!"
    index.exposed = True


class HostedWSGI(object):
    _cp_filters = [WSGIAppFilter(test_app),]


cherrypy.tree.mount(Root(), '')
cherrypy.tree.mount(HostedWSGI(), '/hosted/app0')
cherrypy.tree.mount(WSGIApp(test_app), '/hosted/app1')

import helper

cherrypy.config.update({
    'global': {'server.log_to_screen': False,
               'server.environment': 'production',
               'server.show_tracebacks': True,
               'server.socket_host': helper.CPWebCase.HOST,
               'server.socket_port': helper.CPWebCase.PORT,
               },
    '/xmlrpc': {'xmlrpc_filter.on':True},
    '/hosted/app2': {'wsgiapp_filter.on':True,
                     'wsgiapp_filter.app': test_app,
                     'wsgiapp_filter.env_update': {'cp.hosted':True},
                    },
    })


class WSGIAppFilterTest(helper.CPWebCase):
    
    wsgi_output = '''Hello, world!
This is a wsgi app running within CherryPy!'''

    def test_01_standard_app(self):
        self.getPage("/")
        self.assertBody("I'm a regular CherryPy page handler!")

    def test_02_cp_filters(self):
        self.getPage("/hosted/app0")
        self.assertHeader("Content-Type", "text/plain")
        self.assertInBody(self.wsgi_output)

    def test_03_wsgiapp_class(self):
        self.getPage("/hosted/app1")
        self.assertHeader("Content-Type", "text/plain")
        self.assertInBody(self.wsgi_output)

    def test_04_from_config_prog(self):
        self.getPage("/hosted/app2")
        self.assertHeader("Content-Type", "text/plain")
        self.assertInBody(self.wsgi_output)
        self.assertInBody("cp.hosted")
        
if __name__ == '__main__':
    from cherrypy import _cpwsgi
    server_class = _cpwsgi.WSGIServer
    helper.testmain(server_class)

