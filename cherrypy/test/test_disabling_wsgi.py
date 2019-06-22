import cherrypy
from cherrypy.test import helper


class Root(object):
    @cherrypy.expose
    def index(self):
        return 'payload'


class T(helper.CPWebCase):

    @staticmethod
    def setup_server():
        from cherrypy._cpnative_server import CPHTTPServer
        cherrypy.server.httpserver = CPHTTPServer(cherrypy.server)

        cherrypy.tree.mount(root=Root())

    def test_cpnative(self):
        self.getPage('/')
        self.assertStatus('200 OK')
        self.assertBody('payload')
