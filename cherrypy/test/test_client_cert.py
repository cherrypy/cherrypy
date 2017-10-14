"""Tests for client certificate validation."""

import itertools
import socket
import ssl
from os.path import abspath, basename, dirname, join
from six.moves import urllib

import cherrypy
from cherrypy.test import helper


SSL_DIR = join(abspath(dirname(__file__)), 'ssl')
CA_CERT = join(SSL_DIR, 'ca.cert')
CLIENT_KEY = join(SSL_DIR, 'client.key')
CLIENT_CERT = join(SSL_DIR, 'client.cert')
CLIENT_IP_CERT = join(SSL_DIR, 'client_ip.cert')
CLIENT_WILD_CERT = join(SSL_DIR, 'client_wildcard.cert')
CLIENT_WRONG_CA = join(SSL_DIR, 'client_wrong_ca.cert')
CLIENT_WRONG_HOST = join(SSL_DIR, 'client_wrong_host.cert')
SERVER_KEY = join(SSL_DIR, 'server.key')
SERVER_CERT = join(SSL_DIR, 'server.cert')


class ClientCertTests(object):
    scheme = 'https'
    script_name = '/index'

    server_should_reject = False
    server_host  = 'localhost'
    client_host  = 'localhost'
    ca_chain = CA_CERT
    client_cert = CLIENT_CERT
    verify_mode = 'none'  # none, optional, required

    @classmethod
    def setup_server(cls):
        cherrypy.config.update({
            'checker.on': False,
            'engine.autoreload_on': False,
            'server.socket_host': cls.server_host,
            'server.ssl_module': 'builtin',
            'server.ssl_private_key': SERVER_KEY,
            'server.ssl_certificate': SERVER_CERT,
            'server.ssl_certificate_chain': cls.ca_chain,
            'server.ssl_verify_mode': cls.verify_mode,
        })
        # helper.setup_client()
        cls.PORT = cherrypy.server.socket_port
        cls.HOST = cherrypy.server.socket_host

        class Root:
            @cherrypy.expose
            def index(self):
                return 'ok'

        cherrypy.tree.mount(Root())

    # @classmethod
    # def teardown_class(self):
    #     # cherrypy.config.update({
    #     #     'server.ssl_private_key': helper.serverpem,
    #     #     'server.ssl_certificate': helper.serverpem,
    #     #     'server.ssl_certificate_chain': None,
    #     #     'server.ssl_verify_mode': None,
    #     # })
    #     # cherrypy.engine.exit()
    #     helper.CPWebCase.teardown_class()
    #     cherrypy.engine.exit()
    #     cherrypy.config.reset()

    def test_connect(self):
        context = ssl.create_default_context(cafile=self.ca_chain)
        context.load_cert_chain(self.client_cert, keyfile=CLIENT_KEY)
        context.check_hostname = False

        if self.server_should_reject:
            self.assertRaises(
                urllib.error.URLError,
                urllib.request.urlopen,
                self.base(),
                context=context)
        else:
            self.assertEqual(
                b'ok',
                urllib.request.urlopen(
                    self.base(), context=context).read())


BAD_CLIENT_CERTS = [CLIENT_WRONG_CA]
GOOD_CLIENT_CERTS = [CLIENT_CERT, CLIENT_IP_CERT, CLIENT_WILD_CERT]
SERVER_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']
CLIENT_HOSTS = ['localhost']

TESTS = [
    {'server_should_reject': False,
     'settings': {'verify_mode': [None, 'none', 'optional', 'required'],
                  'client_cert': GOOD_CLIENT_CERTS}},
    {'server_should_reject': False,
     'settings': {'verify_mode': [None, 'none'],
                  'client_cert': BAD_CLIENT_CERTS}},
    {'server_should_reject': True,
     'settings': {'verify_mode': ['optional', 'required'],
                  'client_cert': BAD_CLIENT_CERTS}},
    {'server_should_reject': False,
     'settings': {'verify_mode': ['optional', 'required'],
                  'client_cert': [CLIENT_WRONG_HOST]}},
]
for client_host, server_host in itertools.product(CLIENT_HOSTS, SERVER_HOSTS):
    for tests in TESTS:
        combos = []
        for attr,vals in tests['settings'].items():
            combos.append([(attr, val) for val in vals])

        for settings in itertools.product(*combos):
            attrs = dict(settings,
                         server_host=server_host,
                         client_host=client_host,
                         server_should_reject=tests['server_should_reject'])

            namef = 'ClientCertTest_{server}_{verify_mode}_{what}_{cert}'
            name = namef.format(
                server=server_host,
                verify_mode=attrs['verify_mode'],
                what=('reject' if attrs['server_should_reject'] else 'allow'),
                cert=basename(attrs['client_cert']).replace('.', '_'))

            class_ = type(name, (ClientCertTests, helper.CPWebCase), attrs)
            class_.test_gc = None
            globals()[name] = class_
            del class_
