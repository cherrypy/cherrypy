import test
test.prefer_parent_path()

import httplib
import socket

import cherrypy


pov = 'pPeErRsSiIsStTeEnNcCeE oOfF vViIsSiIoOnN'

def setup_server():
    class Root:
        
        def index(self):
            return pov
        index.exposed = True
        page1 = index
        page2 = index
        page3 = index
        
        def hello(self):
            return "Hello, world!"
        hello.exposed = True
        
        def stream(self):
            for x in xrange(10):
                yield str(x)
        stream.exposed = True
        stream._cp_config = {'stream_response': True}
    
    cherrypy.tree.mount(Root())
    cherrypy.config.update({
        'log_to_screen': False,
        'environment': 'production',
        })


import helper

class ConnectionTests(helper.CPWebCase):
    
    def test_HTTP11(self):
        self.PROTOCOL = "HTTP/1.1"
        
        # Set our HTTP_CONN to an instance so it persists between requests.
        self.HTTP_CONN = httplib.HTTPConnection(self.HOST, self.PORT)
        # Don't automatically re-connect
        self.HTTP_CONN.auto_open = False
        self.HTTP_CONN.connect()
        
        # Make the first request and assert there's no "Connection: close".
        self.getPage("/")
        self.assertStatus('200 OK')
        self.assertBody(pov)
        self.assertNoHeader("Connection")
        
        # Make another request on the same connection.
        self.getPage("/page1")
        self.assertStatus('200 OK')
        self.assertBody(pov)
        self.assertNoHeader("Connection")
        
        # Make another, streamed request on the same connection.
        # Streamed output closes the connection to determine transfer-length.
        self.getPage("/stream")
        self.assertStatus('200 OK')
        self.assertBody('0123456789')
        self.assertHeader("Connection", "close")
        
        # Make another request on the same connection, which should error.
        self.assertRaises(httplib.NotConnected, self.getPage, "/")
        
        # Test client-side close.
        self.HTTP_CONN = httplib.HTTPConnection(self.HOST, self.PORT)
        self.getPage("/page2", headers=[("Connection", "close")])
        self.assertStatus('200 OK')
        self.assertBody(pov)
        self.assertHeader("Connection", "close")
    
    def test_HTTP11_pipelining(self):
        # Test pipelining. httplib doesn't support this directly.
        conn = httplib.HTTPConnection(self.HOST, self.PORT)
        conn.auto_open = False
        conn.connect()
        
        # Put request 1
        conn.putrequest("GET", "/", skip_host=True)
        conn.putheader("Host", self.HOST)
        conn.endheaders()
        
        # Put request 2
        conn._output('GET /hello HTTP/1.1')
        conn._output("Host: %s" % self.HOST)
        conn._send_output()
        
        # Retrieve response 1
        response = conn.response_class(conn.sock, method="GET")
        response.begin()
        body = response.read()
        self.assertEqual(response.status, 200)
        self.assertEqual(body, pov)
        
        # Retrieve response 2
        response = conn.response_class(conn.sock, method="GET")
        response.begin()
        body = response.read()
        self.assertEqual(response.status, 200)
        self.assertEqual(body, "Hello, world!")
        
        conn.close()
    
    def test_HTTP10(self):
        self.PROTOCOL = "HTTP/1.1"
        self.HTTP_CONN = httplib.HTTPConnection
        
        # Test a normal HTTP/1.0 request.
        self.getPage("/page2", protocol="HTTP/1.0")
        self.assertStatus('200 OK')
        self.assertBody(pov)
        self.assertNoHeader("Connection")
        
        # Test a keep-alive HTTP/1.0 request.
        self.HTTP_CONN = httplib.HTTPConnection(self.HOST, self.PORT)
        self.getPage("/page3", headers=[("Connection", "Keep-Alive")],
                     protocol="HTTP/1.0")
        self.assertStatus('200 OK')
        self.assertBody(pov)
        self.assertHeader("Connection", "Keep-Alive")
        
        # Test a keep-alive HTTP/1.0 request.
        self.getPage("/page3", protocol="HTTP/1.0")
        self.assertStatus('200 OK')
        self.assertBody(pov)
        self.assertNoHeader("Connection")


if __name__ == "__main__":
    setup_server()
    helper.testmain()
