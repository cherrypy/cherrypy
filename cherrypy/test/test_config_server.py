"""Tests for the CherryPy configuration system."""

from cherrypy.test import test
test.prefer_parent_path()

import os, sys
localDir = os.path.join(os.getcwd(), os.path.dirname(__file__))
import StringIO

import cherrypy


def setup_server():
    
    class Root:
        def index(self):
            return cherrypy.request.wsgi_environ['SERVER_PORT']
        index.exposed = True
        
        def upload(self, file):
            return "Size: %s" % len(file.file.read())
        upload.exposed = True
    
    cherrypy.tree.mount(Root())
    
    cherrypy.config.update({
        'environment': 'test_suite',
        'server.socket_host': '0.0.0.0',
        'server.socket_port': 9876,
        'server.max_request_body_size': 200,
        'server.max_request_header_size': 500,
        
        # Test explicit server.instance
        'server.2.instance': 'cherrypy._cpwsgi_server.CPWSGIServer',
        'server.2.socket_port': 9877,
        
        # Test non-numeric <servername>
        # Also test default server.instance = builtin server
        'server.yetanother.socket_port': 9878,
        })


#                             Client-side code                             #

from cherrypy.test import helper

class ServerConfigTests(helper.CPWebCase):
    
    PORT = 9876
    
    def testBasicConfig(self):
        self.getPage("/")
        self.assertBody(str(self.PORT))
    
    def testAdditionalServers(self):
        self.PORT = 9877
        self.getPage("/")
        self.assertBody(str(self.PORT))
        self.PORT = 9878
        self.getPage("/")
        self.assertBody(str(self.PORT))
    
    def testMaxRequestSize(self):
        if getattr(cherrypy.server, "using_apache", False):
            print "skipped due to known Apache differences...",
            return
        
        for size in (500, 5000, 50000):
            self.getPage("/", headers=[('From', "x" * 500)])
            self.assertStatus(413)
        
        # Test for http://www.cherrypy.org/ticket/421
        # (Incorrect border condition in readline of SizeCheckWrapper).
        # This hangs in rev 891 and earlier.
        lines256 = "x" * 248
        self.getPage("/",
                     headers=[('Host', '%s:%s' % (self.HOST, self.PORT)),
                              ('From', lines256)])
        
        # Test upload
        body = """--x
Content-Disposition: form-data; name="file"; filename="hello.txt"
Content-Type: text/plain

%s
--x--
"""
        b = body % ("x" * 96)
        h = [("Content-type", "multipart/form-data; boundary=x"),
             ("Content-Length", len(b))]
        self.getPage('/upload', h, "POST", b)
        self.assertBody('Size: 96')
        
        b = body % ("x" * 200)
        h = [("Content-type", "multipart/form-data; boundary=x"),
             ("Content-Length", len(b))]
        self.getPage('/upload', h, "POST", b)
        self.assertStatus(413)



if __name__ == '__main__':
    setup_server()
    helper.testmain()
