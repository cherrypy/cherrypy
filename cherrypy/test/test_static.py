from cherrypy.test import test
test.prefer_parent_path()

import os
curdir = os.path.join(os.getcwd(), os.path.dirname(__file__))
has_space_filepath = os.path.join(curdir, 'static', 'has space.html')
import threading

import cherrypy

def setup_server():
    if not os.path.exists(has_space_filepath):
        file(has_space_filepath, 'wb').write('Hello, world\r\n')
        
    class Root:
        pass

    class Static:
        
        def index(self):
            return 'You want the Baron? You can have the Baron!'
        index.exposed = True
        
        def dynamic(self):
            return "This is a DYNAMIC page"
        dynamic.exposed = True
    
    
    cherrypy.config.update({'environment': 'test_suite'})
    
    root = Root()
    root.static = Static()
    
    rootconf = {
        '/static': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': 'static',
            'tools.staticdir.root': curdir,
        },
        '/style.css': {
            'tools.staticfile.on': True,
            'tools.staticfile.filename': os.path.join(curdir, 'style.css'),
        },
        '/docroot': {
            'tools.staticdir.on': True,
            'tools.staticdir.root': curdir,
            'tools.staticdir.dir': 'static',
            'tools.staticdir.index': 'index.html',
        },
        '/error': {
            'tools.staticdir.on': True,
            'request.show_tracebacks': True,
        },
        }
    rootApp = cherrypy.Application(root)
    rootApp.merge(rootconf)
    
    test_app_conf = {
        '/test': {
            'tools.staticdir.index': 'index.html',
            'tools.staticdir.on': True,
            'tools.staticdir.root': curdir,
            'tools.staticdir.dir': 'static',
            },
        }
    testApp = cherrypy.Application(Static())
    testApp.merge(test_app_conf)
    
    vhost = cherrypy._cpwsgi.VirtualHost(rootApp, {'virt.net': testApp})
    cherrypy.tree.graft(vhost)


def teardown_server():
    if os.path.exists(has_space_filepath):
        try:
            os.unlink(has_space_filepath)
        except:
            pass
        
from cherrypy.test import helper

class StaticTest(helper.CPWebCase):
    
    def testStatic(self):
        self.getPage("/static/index.html")
        self.assertStatus('200 OK')
        self.assertHeader('Content-Type', 'text/html')
        self.assertBody('Hello, world\r\n')
        
        # Using a staticdir.root value in a subdir...
        self.getPage("/docroot/index.html")
        self.assertStatus('200 OK')
        self.assertHeader('Content-Type', 'text/html')
        self.assertBody('Hello, world\r\n')
        
        # Check a filename with spaces in it
        self.getPage("/static/has%20space.html")
        self.assertStatus('200 OK')
        self.assertHeader('Content-Type', 'text/html')
        self.assertBody('Hello, world\r\n')
        
        self.getPage("/style.css")
        self.assertStatus('200 OK')
        self.assertHeader('Content-Type', 'text/css')
        # Note: The body should be exactly 'Dummy stylesheet\n', but
        #   unfortunately some tools such as WinZip sometimes turn \n
        #   into \r\n on Windows when extracting the CherryPy tarball so
        #   we just check the content
        self.assertMatchesBody('^Dummy stylesheet')
    
    def test_fallthrough(self):
        # Test that NotFound will then try dynamic handlers (see [878]).
        self.getPage("/static/dynamic")
        self.assertBody("This is a DYNAMIC page")
        
        # Check a directory via fall-through to dynamic handler.
        self.getPage("/static/")
        self.assertStatus('200 OK')
        self.assertHeader('Content-Type', 'text/html')
        self.assertBody('You want the Baron? You can have the Baron!')
    
    def test_index(self):
        # Check a directory via "staticdir.index".
        self.getPage("/docroot/")
        self.assertStatus('200 OK')
        self.assertHeader('Content-Type', 'text/html')
        self.assertBody('Hello, world\r\n')
        # The same page should be returned even if redirected.
        self.getPage("/docroot")
        self.assertStatus((302, 303))
        self.assertHeader('Location', '%s/docroot/' % self.base())
        self.assertMatchesBody("This resource .* at <a href='%s/docroot/'>"
                               "%s/docroot/</a>." % (self.base(), self.base()))
    
    def test_config_errors(self):
        # Check that we get an error if no .file or .dir
        self.getPage("/error/thing.html")
        self.assertErrorPage(500)
        self.assertInBody("TypeError: staticdir() takes at least 2 "
                          "arguments (0 given)")
    
    def test_security(self):
        # Test up-level security
        self.getPage("/static/../../test/style.css")
        self.assertStatus((400, 403))
    
    def test_modif(self):
        # Test modified-since on a reasonably-large file
        self.getPage("/static/dirback.jpg")
        self.assertStatus("200 OK")
        lastmod = ""
        for k, v in self.headers:
            if k == 'Last-Modified':
                lastmod = v
        ims = ("If-Modified-Since", lastmod)
        self.getPage("/static/dirback.jpg", headers=[ims])
        self.assertStatus(304)
        self.assertNoHeader("Content-Type")
        self.assertNoHeader("Content-Length")
        self.assertNoHeader("Content-Disposition")
        self.assertBody("")
    
    def test_755_vhost(self):
        self.getPage("/test/", [('Host', 'virt.net')])
        self.assertStatus(200)
        self.getPage("/test", [('Host', 'virt.net')])
        self.assertStatus((302, 303))
        self.assertHeader('Location', self.scheme + '://virt.net/test/')


if __name__ == "__main__":
    setup_server()
    helper.testmain()
