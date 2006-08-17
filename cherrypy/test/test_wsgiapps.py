import test
test.prefer_parent_path()


def setup_server():
    import os
    curdir = os.path.join(os.getcwd(), os.path.dirname(__file__))
    
    import cherrypy
    
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

    def reversing_middleware(app):
        def _app(environ, start_response):
            results = app(environ, start_response)
            if not isinstance(results, basestring):
                results = "".join(results)
            results = list(results)
            results.reverse()
            return "".join(results)
        return _app
    
    class Root:
        def index(self):
            return "I'm a regular CherryPy page handler!"
        index.exposed = True
    
    
    class HostedWSGI(object):
        _cp_config = {'tools.wsgiapp.on': True,
                      'tools.wsgiapp.app': test_app,
                      }
    
    cherrypy.config.update({'log_to_screen': False,
                            'environment': 'production',
                            'show_tracebacks': True,
                            })
    cherrypy.tree.mount(Root())
    
    conf0 = {'/static': {'tools.staticdir.on': True,
                         'tools.staticdir.root': curdir,
                         'tools.staticdir.dir': 'static',
                         }}
    cherrypy.tree.mount(HostedWSGI(), '/hosted/app0', conf0)
    cherrypy.tree.graft(test_app, '/hosted/app1')
    
    app = cherrypy.Application(Root(), None)
    cherrypy.tree.graft(reversing_middleware(app), '/hosted/app2')

import helper


class WSGIAppTest(helper.CPWebCase):
    
    wsgi_output = '''Hello, world!
This is a wsgi app running within CherryPy!'''

    def test_01_standard_app(self):
        self.getPage("/")
        self.assertBody("I'm a regular CherryPy page handler!")
    
    def test_02_wrapped_wsgi(self):
        self.getPage("/hosted/app0")
        self.assertHeader("Content-Type", "text/plain")
        self.assertInBody(self.wsgi_output)
    
    def test_03_static_subdir(self):
        self.getPage("/hosted/app0/static/index.html")
        self.assertStatus('200 OK')
        self.assertHeader('Content-Type', 'text/html')
        self.assertBody('Hello, world\r\n')
    
    def test_04_pure_wsgi(self):
        self.getPage("/hosted/app1")
        self.assertHeader("Content-Type", "text/plain")
        self.assertInBody(self.wsgi_output)

    def test_05_wrapped_cp_app(self):
        self.getPage("/hosted/app2/")
        body = list("I'm a regular CherryPy page handler!")
        body.reverse()
        body = "".join(body)
        self.assertInBody(body)

if __name__ == '__main__':
    setup_server()
    helper.testmain()

