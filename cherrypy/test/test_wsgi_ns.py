from cherrypy.test import test
test.prefer_parent_path()

import cherrypy


def setup_server():
    
    class ChangeCase(object):
        
        def __init__(self, app, to=None):
            self.app = app
            self.to = to
        
        def __call__(self, environ, start_response):
            res = ''.join(self.app(environ, start_response))
            return [getattr(res, self.to)()]
    
    def replace(app, map={}):
        def replace_app(environ, start_response):
            for line in app(environ, start_response):
                for k, v in map.iteritems():
                    line = line.replace(k, v)
                yield line
        return replace_app
    
    class Root(object):
        
        def index(self):
            return "HellO WoRlD!"
        index.exposed = True
    
    
    root_conf = {'wsgi.pipeline': [('replace', replace)],
                 'wsgi.replace.map': {'L': 'X', 'l': 'r'},
                 }
    
    cherrypy.config.update({'environment': 'test_suite'})
    
    app = cherrypy.Application(Root())
    app.wsgiapp.pipeline.append(('changecase', ChangeCase))
    app.wsgiapp.config['changecase'] = {'to': 'upper'}
    cherrypy.tree.mount(app, config={'/': root_conf})


from cherrypy.test import helper


class WSGI_Namespace_Test(helper.CPWebCase):
    
    def test_pipeline(self):
        if not cherrypy.server.httpservers:
            print "skipped ",
            return
        
        self.getPage("/")
        # If body is "HEXXO WORXD!", the middleware was applied out of order.
        self.assertBody("HERRO WORRD!")

if __name__ == '__main__':
    setup_server()
    helper.testmain()

