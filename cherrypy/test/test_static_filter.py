import test
test.prefer_parent_path()

import cherrypy
import os


class Root: pass

cherrypy.root = Root()
cherrypy.config.update({
    'global': {
        'staticFilter.on': False,
        'server.logToScreen': False,
        'server.environment': 'production',
    },
    '/static': {
        'staticFilter.on': True,
        'staticFilter.dir': 'static',
    },
    '/style.css': {
        'staticFilter.on': True,
        'staticFilter.file': 'style.css',
    },
    '/docroot': {
        'staticFilter.on': True,
        'staticFilter.root': os.path.join(os.getcwd(), os.path.dirname(__file__)),
        'staticFilter.dir': 'static',
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
        
        # Using a staticFilter.root value...
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
        
        # Check a directory (should currently fail--no provision for it)
        ignore = helper.webtest.ignored_exceptions
        ignore.append(IOError)
        try:
            self.getPage("/static/")
            self.assertErrorPage(500)
        finally:
            ignore.pop()

if __name__ == "__main__":
    helper.testmain()
