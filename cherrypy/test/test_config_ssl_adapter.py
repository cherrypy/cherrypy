"""Tests for the CherryPy ssl adapter configurations."""

import os
import ssl
import cherrypy
from cherrypy.test import helper
from cherrypy._cpcompat import HTTPSConnection

thisDir = os.path.join(os.getcwd(), os.path.dirname(__file__))

#                             Client-side code                             #


class TestConfigBuiltinSSLAdapter(helper.CPWebCase):
    HTTP_CONN = HTTPSConnection
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_context.verify_mode = ssl.CERT_REQUIRED
    ssl_context.load_verify_locations(os.path.join(thisDir, 'test_passwd.pem'))

    @classmethod
    def setup_server(cls):
        cherrypy.config.update(
            {
                'server.ssl_adapter': 'builtin',
                'server.ssl_certificate': os.path.join(
                    thisDir,
                    'test_passwd.pem',
                ),
                'server.ssl_private_key': os.path.join(
                    thisDir,
                    'test_passwd.pem',
                ),
                'server.ssl_certificate_chain': os.path.join(
                    thisDir,
                    'test_passwd.pem',
                ),
                'server.ssl_private_key_password': '123456',
            },
        )

        class Root:
            @cherrypy.expose
            def index(self):
                return 'Hello world!'

        cherrypy.tree.mount(Root())

    @classmethod
    def teardown_class(cls):
        cherrypy.config.update(
            {
                'server.ssl_adapter': None,
                'server.ssl_certificate': None,
                'server.ssl_private_key': None,
                'server.ssl_certificate_chain': None,
                'server.ssl_private_key_password': None,
            },
        )
        super().teardown_class()

    def testBuiltinSSLAdapter(self):
        self.getPage('/')
        self.assertStatus(200)
        self.assertBody('Hello world!')


class TestConfigPyOpenSSLAdapter(helper.CPWebCase):
    HTTP_CONN = HTTPSConnection
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_context.verify_mode = ssl.CERT_REQUIRED
    ssl_context.load_verify_locations(os.path.join(thisDir, 'test_passwd.pem'))

    @classmethod
    def setup_server(cls):
        cherrypy.config.update(
            {
                'server.ssl_adapter': 'pyopenssl',
                'server.ssl_certificate': os.path.join(
                    thisDir,
                    'test_passwd.pem',
                ),
                'server.ssl_private_key': os.path.join(
                    thisDir,
                    'test_passwd.pem',
                ),
                'server.ssl_certificate_chain': os.path.join(
                    thisDir,
                    'test_passwd.pem',
                ),
                'server.ssl_private_key_password': '123456',
            },
        )

        class Root:
            @cherrypy.expose
            def index(self):
                return 'Hello world!'

        cherrypy.tree.mount(Root())

    @classmethod
    def teardown_class(cls):
        cherrypy.config.update(
            {
                'server.ssl_adapter': None,
                'server.ssl_certificate': None,
                'server.ssl_private_key': None,
                'server.ssl_certificate_chain': None,
                'server.ssl_private_key_password': None,
            },
        )
        super().teardown_class()

    def testPyOpenSSLAdapter(self):
        self.getPage('/')
        self.assertStatus(200)
        self.assertBody('Hello world!')
