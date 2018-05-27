"""Docstring."""

import pytest
from requests_toolbelt import sessions

import cherrypy._cpnative_server


@pytest.fixture
def cp_native_server(request):
    """A native server."""
    class Root(object):
        @cherrypy.expose
        def index(self):
            return 'Hello World!'

    cls = cherrypy._cpnative_server.CPHTTPServer
    cherrypy.server.httpserver = cls(cherrypy.server)

    cherrypy.tree.mount(Root(), '/')
    cherrypy.engine.start()
    request.addfinalizer(cherrypy.engine.stop)
    url = 'http://localhost:{cherrypy.server.socket_port}'.format(**globals())
    return sessions.BaseUrlSession(url)


def test_basic_request(cp_native_server):
    """A request to a native server should succeed."""
    cp_native_server.get('/')
