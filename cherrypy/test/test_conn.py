from cherrypy.test import test
test.prefer_parent_path()

import httplib
import socket

import cherrypy
from cherrypy.test import webtest


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
        stream._cp_config = {'response.stream': True}
        
        def upload(self):
            return ("thanks for '%s' (%s)" %
                    (cherrypy.request.body.read(),
                     cherrypy.request.headers['Content-Type']))
        upload.exposed = True
    
    cherrypy.tree.mount(Root())
    cherrypy.config.update({
        'server.max_request_body_size': 100,
        'environment': 'test_suite',
        })


from cherrypy.test import helper

class ConnectionTests(helper.CPWebCase):
    
    def test_HTTP11(self):
        if cherrypy.server.protocol_version != "HTTP/1.1":
            print "skipped ",
            return
        
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
        self.getPage("/stream")
        self.assertStatus('200 OK')
        self.assertBody('0123456789')
        self.assertNoHeader("Content-Length")
        # Streamed output will either close the connection, or use
        # chunked encoding, to determine transfer-length.
        chunked_response = False
        for k, v in self.headers:
            if k.lower() == "transfer-encoding":
                if str(v) == "chunked":
                    chunked_response = True
        if not chunked_response:
            self.assertHeader("Connection", "close")
            
            # Make another request on the same connection, which should error.
            self.assertRaises(httplib.NotConnected, self.getPage, "/")
        
        # Test client-side close.
        self.HTTP_CONN = httplib.HTTPConnection(self.HOST, self.PORT)
        self.HTTP_CONN.auto_open = False
        self.HTTP_CONN.connect()
        self.getPage("/page2", headers=[("Connection", "close")])
        self.assertStatus('200 OK')
        self.assertBody(pov)
        self.assertHeader("Connection", "close")
        
        # Make another request on the same connection, which should error.
        self.assertRaises(httplib.NotConnected, self.getPage, "/")
    
    def test_HTTP11_pipelining(self):
        if cherrypy.server.protocol_version != "HTTP/1.1":
            print "skipped ",
            return
        
        self.PROTOCOL = "HTTP/1.1"
        
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
    
    def test_100_Continue(self):
        if cherrypy.server.protocol_version != "HTTP/1.1":
            print "skipped ",
            return
        
        self.PROTOCOL = "HTTP/1.1"
        
        conn = httplib.HTTPConnection(self.HOST, self.PORT)
        conn.auto_open = False
        conn.connect()
        
        # Try a page without an Expect request header first.
        # Note that httplib's response.begin automatically ignores
        # 100 Continue responses, so we must manually check for it.
        conn.putrequest("POST", "/upload", skip_host=True)
        conn.putheader("Host", self.HOST)
        conn.putheader("Content-Type", "text/plain")
        conn.putheader("Content-Length", "4")
        conn.endheaders()
        conn.send("d'oh")
        response = conn.response_class(conn.sock, method="POST")
        version, status, reason = response._read_status()
        self.assertNotEqual(status, 100)
        conn.close()
        
        # Now try a page with an Expect header...
        conn.connect()
        conn.putrequest("POST", "/upload", skip_host=True)
        conn.putheader("Host", self.HOST)
        conn.putheader("Content-Type", "text/plain")
        conn.putheader("Content-Length", "17")
        conn.putheader("Expect", "100-continue")
        conn.endheaders()
        response = conn.response_class(conn.sock, method="POST")
        
        # ...assert and then skip the 100 response
        version, status, reason = response._read_status()
        self.assertEqual(status, 100)
        while True:
            skip = response.fp.readline().strip()
            if not skip:
                break
        
        # ...send the body
        conn.send("I am a small file")
        
        # ...get the final response
        response.begin()
        self.status, self.headers, self.body = webtest.shb(response)
        self.assertStatus(200)
        self.assertBody("thanks for 'I am a small file' (text/plain)")
    
    def test_Chunked_Encoding(self):
        if cherrypy.server.protocol_version != "HTTP/1.1":
            print "skipped ",
            return
        
        self.PROTOCOL = "HTTP/1.1"
        
        # Set our HTTP_CONN to an instance so it persists between requests.
        conn = httplib.HTTPConnection(self.HOST, self.PORT)
        
        # Try a normal chunked request
        body = ("8\r\nxx\r\nxxxx\r\n5\r\nyyyyy\r\n0\r\n"
                "Content-Type: application/x-json\r\n\r\n")
        conn.putrequest("POST", "/upload", skip_host=True)
        conn.putheader("Host", self.HOST)
        conn.putheader("Transfer-Encoding", "chunked")
        conn.putheader("Trailer", "Content-Type")
        # Note that this is somewhat malformed:
        # we shouldn't be sending Content-Length.
        # RFC 2616 says the server should ignore it.
        conn.putheader("Content-Length", len(body))
        conn.endheaders()
        conn.send(body)
        response = conn.getresponse()
        self.status, self.headers, self.body = webtest.shb(response)
        self.assertStatus('200 OK')
        self.assertBody("thanks for 'xx\r\nxxxxyyyyy' (application/x-json)")
        
        # Try a chunked request that exceeds server.max_request_body_size.
        # Note that the delimiters and trailer are included.
        body = "5f\r\n" + ("x" * 95) + "\r\n0\r\n\r\n"
        conn.putrequest("POST", "/upload", skip_host=True)
        conn.putheader("Host", self.HOST)
        conn.putheader("Transfer-Encoding", "chunked")
        conn.putheader("Content-Type", "text/plain")
##        conn.putheader("Content-Length", len(body))
        conn.endheaders()
        conn.send(body)
        response = conn.getresponse()
        self.status, self.headers, self.body = webtest.shb(response)
        self.assertStatus(413)
        self.assertBody("")
    
    def test_HTTP10(self):
        self.PROTOCOL = "HTTP/1.0"
        self.HTTP_CONN = httplib.HTTPConnection
        
        # Test a normal HTTP/1.0 request.
        self.getPage("/page2")
        self.assertStatus('200 OK')
        self.assertBody(pov)
        # Apache, for example, may emit a Connection header even for HTTP/1.0
##        self.assertNoHeader("Connection")
        
        # Test a keep-alive HTTP/1.0 request.
        self.HTTP_CONN = httplib.HTTPConnection(self.HOST, self.PORT)
        self.HTTP_CONN.auto_open = False
        self.HTTP_CONN.connect()
        
        self.getPage("/page3", headers=[("Connection", "Keep-Alive")])
        self.assertStatus('200 OK')
        self.assertBody(pov)
        self.assertHeader("Connection", "Keep-Alive")
        
        # Remove the keep-alive header again.
        self.getPage("/page3")
        self.assertStatus('200 OK')
        self.assertBody(pov)
        # Apache, for example, may emit a Connection header even for HTTP/1.0
##        self.assertNoHeader("Connection")


if __name__ == "__main__":
    setup_server()
    helper.testmain()
