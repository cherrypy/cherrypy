"""Tests for managing HTTP issues (malformed requests, etc).

Some of these tests check timeouts, etcetera, and therefore take a long
time to run. Therefore, this module should probably not be included in
the 'comprehensive' test suite (test.py).
"""

from cherrypy.test import test
test.prefer_parent_path()

import httplib
import cherrypy


def setup_server():
    
    class Root:
        def index(self, *args, **kwargs):
            return "Hello world!"
        index.exposed = True
    
    cherrypy.tree.mount(Root())
    cherrypy.config.update({'environment': 'test_suite'})


from cherrypy.test import helper

class HTTPTests(helper.CPWebCase):
    
    def test_sockets(self):
        # By not including a Content-Length header, cgi.FieldStorage
        # will hang. Verify that CP times out the socket and responds
        # with 411 Length Required.
        c = httplib.HTTPConnection("127.0.0.1:%s" % self.PORT)
        c.request("POST", "/")
        self.assertEqual(c.getresponse().status, 411)


if __name__ == '__main__':
    setup_server()
    helper.testmain()
