import test
test.prefer_parent_path()

import os
curdir = os.path.join(os.getcwd(), os.path.dirname(__file__))

import cherrypy
from cherrypy.lib import cptools


class Root:
    pass

class Static:
    
    def index(self):
        return 'You want the Baron? You can have the Baron!'
    index.exposed = True
    
    def dynamic(self):
        return "This is a DYNAMIC page"
    dynamic.exposed = True


cherrypy.root = Root()
cherrypy.root.static = Static()

cherrypy.config.update({
    'global': {
        'static_filter.on': False,
        'server.log_to_screen': False,
        'server.environment': 'production',
    },
    '/static': {
        'static_filter.on': True,
        'static_filter.dir': 'static',
    },
    '/style.css': {
        'static_filter.on': True,
        'static_filter.file': 'style.css',
    },
    '/docroot': {
        'static_filter.on': True,
        'static_filter.root': curdir,
        'static_filter.dir': 'static',
        'static_filter.index': 'index.html',
    },
})

import helper

class StaticFilterTest(helper.CPWebCase):
    
    def testStaticFilter(self):
        # This should resolve relative to cherrypy.root.__module__.
        self.getPage("/static/index.html")
        self.assertStatus('200 OK')
        self.assertHeader('Content-Type', 'text/html')
        self.assertBody('Hello, world\r\n')
        
        # Using a static_filter.root value...
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
        
        # Test that NotFound will then try dynamic handlers (see [878]).
        self.getPage("/static/dynamic")
        self.assertBody("This is a DYNAMIC page")
        
        # Check a directory via fall-through to dynamic handler.
        self.getPage("/static/")
        self.assertStatus('200 OK')
        self.assertHeader('Content-Type', 'text/html')
        self.assertBody('You want the Baron? You can have the Baron!')
        
        # Check a directory via "static_filter.index".
        self.getPage("/docroot/")
        self.assertStatus('200 OK')
        self.assertHeader('Content-Type', 'text/html')
        self.assertBody('Hello, world\r\n')
        # The same page should be returned even if redirected.
        self.getPage("/docroot")
        self.assertStatus('200 OK')
        self.assertHeader('Content-Type', 'text/html')
        self.assertBody('Hello, world\r\n')


if __name__ == "__main__":
    helper.testmain()
