import test
test.prefer_parent_path()

import cherrypy
from cherrypy.lib import cptools


def setup_server():
    class Root:
        pass
    
    
    class Accept:
        def index(self):
            cptools.accept()
            return '<a href="feed">Atom feed</a>'
        index.exposed = True
        
        def feed(self):
            cptools.accept(media='application/atom+xml')
            return """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
    <title>Unknown Blog</title>
</feed>"""
        feed.exposed = True
        
        def select(self):
            mtype = cptools.accept(['text/html', 'text/plain'])
            if mtype == 'text/html':
                return "<h2>Page Title</h2>"
            else:
                return "PAGE TITLE"
        select.exposed = True
    
    class Referer:
        def accept(self):
            cptools.referer(pattern=r'http://[^/]*thisdomain\.com')
            return "Accepted!"
        accept.exposed = True
        
        def reject(self):
            cptools.referer(pattern=r'http://[^/]*thisdomain\.com',
                            accept=False, accept_missing=True)
            return "Accepted!"
        reject.exposed = True
    
    root = Root()
    root.referer = Referer()
    root.accept = Accept()
    cherrypy.root = root
    cherrypy.config.update({
            'server.log_to_screen': False,
            'server.environment': 'production',
    })


import helper


class RefererTest(helper.CPWebCase):
    
    def testReferer(self):
        self.getPage('/referer/accept')
        self.assertErrorPage(403, 'Forbidden Referer header.')
        
        self.getPage('/referer/accept',
                     headers=[('Referer', 'http://www.thisdomain.com/')])
        self.assertStatus(200)
        self.assertBody('Accepted!')
        
        # Reject
        self.getPage('/referer/reject')
        self.assertStatus(200)
        self.assertBody('Accepted!')
        
        self.getPage('/referer/reject',
                     headers=[('Referer', 'http://www.thisdomain.com/')])
        self.assertErrorPage(403, 'Forbidden Referer header.')


class AcceptTest(helper.CPWebCase):
    
    def test_Accept_Tool(self):
        # Test with no header provided
        self.getPage('/accept/feed')
        self.assertStatus(200)
        self.assertInBody('<title>Unknown Blog</title>')
        
        # Specify exact media type
        self.getPage('/accept/feed', headers=[('Accept', 'application/atom+xml')])
        self.assertStatus(200)
        self.assertInBody('<title>Unknown Blog</title>')
        
        # Specify matching media range
        self.getPage('/accept/feed', headers=[('Accept', 'application/*')])
        self.assertStatus(200)
        self.assertInBody('<title>Unknown Blog</title>')
        
        # Specify all media ranges
        self.getPage('/accept/feed', headers=[('Accept', '*/*')])
        self.assertStatus(200)
        self.assertInBody('<title>Unknown Blog</title>')
        
        # Specify unacceptable media types
        self.getPage('/accept/feed', headers=[('Accept', 'text/html')])
        self.assertErrorPage(406,
                             "Your client sent this Accept header: text/html. "
                             "But this resource only emits these media types: "
                             "application/atom+xml.")
        
        # Test resource where tool is 'on' but media is None (not set).
        self.getPage('/accept/')
        self.assertStatus(200)
        self.assertBody('<a href="feed">Atom feed</a>')
    
    def test_accept_selection(self):
        # Try both our expected media types
        self.getPage('/accept/select', [('Accept', 'text/html')])
        self.assertStatus(200)
        self.assertBody('<h2>Page Title</h2>')
        self.getPage('/accept/select', [('Accept', 'text/plain')])
        self.assertStatus(200)
        self.assertBody('PAGE TITLE')
        self.getPage('/accept/select', [('Accept', 'text/plain, text/*;q=0.5')])
        self.assertStatus(200)
        self.assertBody('PAGE TITLE')
        
        # text/* and */* should prefer text/html since it comes first
        # in our 'media' argument to tools.accept
        self.getPage('/accept/select', [('Accept', 'text/*')])
        self.assertStatus(200)
        self.assertBody('<h2>Page Title</h2>')
        self.getPage('/accept/select', [('Accept', '*/*')])
        self.assertStatus(200)
        self.assertBody('<h2>Page Title</h2>')
        
        # Try unacceptable media types
        self.getPage('/accept/select', [('Accept', 'application/xml')])
        self.assertErrorPage(406,
                             "Your client sent this Accept header: application/xml. "
                             "But this resource only emits these media types: "
                             "text/html, text/plain.")



if __name__ == "__main__":
    setup_server()
    helper.testmain()
