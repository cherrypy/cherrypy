"""Tests for client certificate validation."""

import itertools
import json
import pytest
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


def subdict(dict_, key_predicate):
    """Return a subset of a dictionary.  Only keys matching `key_predicate` are included."""
    return {k: v for k, v in dict_.items() if key_predicate(k)}


class ClientCertTests(object):
    """Client certificate validation tests."""
    scheme = 'https'
    script_name = '/wsgi_env'

    server_should_reject = False
    server_host = 'localhost'
    client_host = 'localhost'
    ca_chain = CA_CERT
    client_cert = CLIENT_CERT
    verify_mode = None  # None, 'none', 'optional', 'required'

    @classmethod
    def setup_server(cls):
        """Prepare server for test."""
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

        class Root:
            """Test application."""
            @cherrypy.expose
            @cherrypy.tools.json_out()
            def wsgi_env(self):
                """Return client certificate WSGI environment variables."""
                return subdict(
                    cherrypy.request.wsgi_environ,
                    lambda k: k.startswith('SSL_CLIENT_'))

        cherrypy.tree.mount(Root())

    def test_connect(self):
        """If server_should_reject is false, verify the index can be fetched.
        Otherwise, verify that a URLError is raised when connecting.
        """
        context = ssl.create_default_context(cafile=self.ca_chain)
        context.load_cert_chain(self.client_cert, keyfile=CLIENT_KEY)
        context.check_hostname = False

        if self.server_should_reject:
            with pytest.raises(urllib.error.URLError):
                urllib.request.urlopen(self.base(), context=context)
        else:
            self.assert_wsgi_env(context)

    def assert_wsgi_env(self, ssl_context):
        """Verify the response contains WSGI environment variables from our client certificate."""
        if self.verify_mode in (None, 'none'):
            return

        body = urllib.request.urlopen(self.base(), context=ssl_context).read()
        wsgi_env = json.loads(body.decode())
        assert wsgi_env['SSL_CLIENT_S_DN_C'] == 'US'
        assert wsgi_env['SSL_CLIENT_S_DN_CN'] is not None
        assert wsgi_env['SSL_CLIENT_S_DN_O'] == 'CherryPy'
        assert wsgi_env['SSL_CLIENT_S_DN_ST'] == 'XX'
        assert wsgi_env['SSL_CLIENT_I_DN_C'] == 'US'
        assert wsgi_env['SSL_CLIENT_I_DN_L'] == 'XXX'
        assert wsgi_env['SSL_CLIENT_I_DN_O'] == 'CherryPy'
        assert wsgi_env['SSL_CLIENT_I_DN_ST'] == 'XX'


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
        for attr, vals in tests['settings'].items():
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
