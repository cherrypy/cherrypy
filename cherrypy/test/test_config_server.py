"""Tests for the CherryPy configuration system."""

from cherrypy.test import test
test.prefer_parent_path()

import os, sys
localDir = os.path.join(os.getcwd(), os.path.dirname(__file__))
import socket
import StringIO
import time

import cherrypy


def setup_server():
    
    class Root:
        def index(self):
            return cherrypy.request.wsgi_environ['SERVER_PORT']
        index.exposed = True
        
        def upload(self, file):
            return "Size: %s" % len(file.file.read())
        upload.exposed = True
        
        def tinyupload(self, maxlen):
            cherrypy.request.rfile.maxlen = int(maxlen)
            cl = int(cherrypy.request.headers['Content-Length'])
            try:
                body = cherrypy.request.rfile.read(cl)
            except Exception, e:
                if e.__class__.__name__ == 'MaxSizeExceeded':
                    # Post data is too big
                    raise cherrypy.HTTPError(413)
                else:
                    raise
            return body
        tinyupload.exposed = True
        tinyupload._cp_config = {'request.process_request_body': False}
    
    cherrypy.tree.mount(Root())
    
    cherrypy.config.update({
        'server.socket_host': '0.0.0.0',
        'server.socket_port': 9876,
        'server.max_request_body_size': 200,
        'server.max_request_header_size': 500,
        'server.socket_timeout': 0.5,
        
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
    
    def testMaxRequestSizePerHandler(self):
        if getattr(cherrypy.server, "using_apache", False):
            cherrypy.py3print("skipped due to known Apache differences...", end=' ')
            return
        
        self.getPage('/tinyupload?maxlen=100', method="POST", body="x" * 100)
        self.assertStatus(200)
        self.assertBody("x" * 100)
        self.getPage('/tinyupload?maxlen=100', method="POST", body="x" * 101)
        self.assertStatus(413)
    
    def testMaxRequestSize(self):
        if getattr(cherrypy.server, "using_apache", False):
            cherrypy.py3print("skipped due to known Apache differences...", end=' ')
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
        body = '\r\n'.join([
            '--x',
            'Content-Disposition: form-data; name="file"; filename="hello.txt"',
            'Content-Type: text/plain',
            '',
            '%s',
            '--x--'])
        partlen = 200 - len(body)
        b = body % ("x" * partlen)
        h = [("Content-type", "multipart/form-data; boundary=x"),
             ("Content-Length", len(b))]
        self.getPage('/upload', h, "POST", b)
        self.assertBody('Size: %d' % partlen)
        
        b = body % ("x" * 200)
        h = [("Content-type", "multipart/form-data; boundary=x"),
             ("Content-Length", len(b))]
        self.getPage('/upload', h, "POST", b)
        self.assertStatus(413)



if __name__ == '__main__':
    helper.testmain()
