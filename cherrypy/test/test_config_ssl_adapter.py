import pytest
import trustme
import ssl
import cherrypy
from cherrypy._cpcompat import HTTPSConnection
from cherrypy import _cpwsgi_server, _cpnative_server

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import (
    BestAvailableEncryption,
    Encoding,
    PrivateFormat,
    load_pem_private_key,
)


@pytest.fixture(scope='session')
def private_key_password():
    """Provide hardcoded password for private key."""
    return 'криївка'


@pytest.fixture
def ssl_cert_and_key(tmp_path, private_key_password):
    """Create certificate chain and encrypted key as one pem."""
    ca = trustme.CA()
    leaf_cert = ca.issue_cert('localhost', '127.0.0.1', '::1')
    key_as_bytes = leaf_cert.private_key_pem.bytes()
    private_key_object = load_pem_private_key(
        key_as_bytes,
        password=None,
        backend=default_backend(),
    )

    encrypted_key_as_bytes = private_key_object.private_bytes(
        encoding=Encoding.PEM,
        format=PrivateFormat.PKCS8,
        encryption_algorithm=BestAvailableEncryption(
            password=private_key_password.encode('utf-8'),
        ),
    )

    key_file = tmp_path / 'encrypted_cert.pem'
    key_file.write_bytes(
        encrypted_key_as_bytes
        + b''.join(cert.bytes() for cert in leaf_cert.cert_chain_pems)
        + ca.cert_pem.bytes(),
    )

    return key_file


@pytest.fixture
def trusted_ssl_context(ssl_cert_and_key):
    """Provide trusted ssl context for the given certificate."""
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_context.verify_mode = ssl.CERT_REQUIRED
    ssl_context.load_verify_locations(ssl_cert_and_key)
    return ssl_context


@pytest.fixture
def https_server(
    request,
    ssl_cert_and_key,
    adapter_type,
    server_type,
    private_key_password,
):
    """Create server configuration and start server."""

    class Root(object):
        @cherrypy.expose
        def index(self):
            return b'Hello World!'

    cherrypy.config.update(
        {
            'environment': 'test_suite',
            'server.socket_host': '0.0.0.0',
            'server.socket_port': 8000,
            'server.ssl_module': adapter_type,
            'server.ssl_certificate': ssl_cert_and_key,
            'server.ssl_private_key': ssl_cert_and_key,
            'server.ssl_certificate_chain': ssl_cert_and_key,
            'server.ssl_private_key_password': private_key_password,
        },
    )

    cls = server_type
    cherrypy.server.httpserver = cls(cherrypy.server)
    cherrypy.tree.mount(Root(), '/', config={'/': {}})
    cherrypy.engine.start()

    yield

    cherrypy.engine.exit()
    cherrypy.server.httpserver = None
    cherrypy.config.reset()
    cherrypy.config.update(
        {
            'server.ssl_module': None,
            'server.ssl_certificate': None,
            'server.ssl_private_key': None,
            'server.ssl_certificate_chain': None,
            'server.ssl_private_key_password': None,
        },
    )


@pytest.fixture
def https_connection(trusted_ssl_context):
    """Provide https connection object."""
    conn = HTTPSConnection(
        '127.0.0.1',
        port=cherrypy.server.socket_port,
        context=trusted_ssl_context,
    )
    yield conn
    conn.close()


@pytest.fixture
def https_req(https_connection):
    """Create https request and provide response object."""
    https_connection.request('GET', '/')
    resp = https_connection.getresponse()
    yield resp
    resp.close()


@pytest.mark.parametrize('adapter_type', ('builtin', 'pyopenssl'))
@pytest.mark.parametrize(
    'server_type',
    (_cpwsgi_server.CPWSGIServer, _cpnative_server.CPHTTPServer),
    ids=('wsgi-server', 'native-server'),
)
def test_private_key_password_config_option(
    https_server,
    https_req,
    adapter_type,
    server_type,
):
    """Check that private key password configuration works with servers."""
    resp = https_req
    assert resp.read() == b'Hello World!'
    assert resp.status == 200
