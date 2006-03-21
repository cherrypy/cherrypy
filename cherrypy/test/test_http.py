"""Tests for managing HTTP issues (malformed requests, etc).

Some of these tests check timeouts, etcetera, and therefore take a long
time to run. Therefore, this module should probably not be included in
the 'comprehensive' test suite (test.py). Note, however, that we default
to the builtin HTTP server (most tests default to 'serverless').
"""

import test
test.prefer_parent_path()

import httplib
import cherrypy


class Root:
    def index(self, *args, **kwargs):
        return "Hello world!"
    index.exposed = True
cherrypy.tree.mount(Root())

cherrypy.config.update({
    'global': {'server.log_to_screen': False,
               'server.environment': 'production',
               'server.show_tracebacks': True,
               },
})

import helper

class HTTPTests(helper.CPWebCase):
    
    def test_sockets(self):
        if cherrypy.server.httpserver:
            # By not including a Content-Length header, cgi.FieldStorage
            # will hang. Verify that CP times out the socket and responds
            # with 411 Length Required.
            c = httplib.HTTPConnection("localhost:%s" % self.PORT)
            c.request("POST", "/")
            self.assertEqual(c.getresponse().status, 411)


if __name__ == '__main__':
    helper.testmain(server="cherrypy._cpwsgi.WSGIServer")
