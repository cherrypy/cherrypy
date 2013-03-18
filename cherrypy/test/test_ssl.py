import socket
import urllib2
import itertools
from unittest import TestCase
from os.path import abspath, dirname, join

import cherrypy
from cherrypy.wsgiserver import SSLAdapter
from cherrypy.test.https_verifier import VerifiedHTTPSHandler


class HostnameTests(TestCase):
    def assert_matches(self, addr, common_name):
        self.assertTrue(SSLAdapter._matches(addr, common_name),
                        "%s doesn't match %s" % (addr, common_name))
    
    def assert_not_matches(self, addr, common_name):
        self.assertFalse(SSLAdapter._matches(addr, common_name),
                         "%s matches %s" % (addr, common_name))
    
    def test_local_valid(self):
        matcher = SSLAdapter.address_matches
        self.assertTrue(matcher(("localhost",8080), "localhost"))
        self.assertTrue(matcher(("127.0.0.1",8080), "localhost"))
        self.assertTrue(matcher(("localhost",8080), "127.0.0.1"))
        self.assertTrue(matcher(("127.0.0.1",8080), "127.0.0.1"))
        self.assertTrue(matcher(("localhost",8080), "*.localhost"))
        self.assertTrue(matcher(("127.0.0.1",8080), "*.localhost"))
    
    def test_local_invalid(self):
        matcher = SSLAdapter.address_matches
        self.assertFalse(matcher(("localhost",8080), "1.2.3.4"))
        self.assertFalse(matcher(("localhost",8080), "example.com"))
        self.assertFalse(matcher(("localhost",8080), "*.example.com"))
    
    def test_wild_matches(self):
        self.assertTrue(SSLAdapter._matches("localhost", "*.localhost"))
        self.assertTrue(SSLAdapter._matches("sub.localhost", "*.localhost"))
        self.assertTrue(SSLAdapter._matches("a.b.localhost", "*.localhost"))
        self.assertTrue(SSLAdapter._matches("example.com", "*.example.com"))
        self.assertTrue(SSLAdapter._matches("sub.example.com", "*.example.com"))
        self.assertTrue(SSLAdapter._matches("a.b.example.com", "*.example.com"))
    
    def test_wild_nonmatches(self):
        self.assertFalse(SSLAdapter._matches("localhost", "localhost.*"))
        self.assertFalse(SSLAdapter._matches("a.b.localhost", "a.*.localhost"))
        self.assertFalse(SSLAdapter._matches("not_localhost", "*.localhost"))
        self.assertFalse(SSLAdapter._matches("not_localhost", "*localhost"))
        self.assertFalse(SSLAdapter._matches("example.com", "example.com.*"))
        self.assertFalse(SSLAdapter._matches("example.com", "example.com*"))
        self.assertFalse(SSLAdapter._matches("example.com", "example.*"))
        self.assertFalse(SSLAdapter._matches("a.b.example.com", "a.*.example.com"))
        self.assertFalse(SSLAdapter._matches("not_example.com", "*.example.com"))
        self.assertFalse(SSLAdapter._matches("not_example.com", "*example.com"))


THIS_DIR = abspath(dirname(__file__))

CA_CERT     = join(THIS_DIR, "ca.cert")

SERVER_KEY        = join(THIS_DIR, "server.key")
SERVER_CERT       = join(THIS_DIR, "server.cert")
SERVER_WRONG_CA   = join(THIS_DIR, "server_wrong_ca.cert")
SERVER_WRONG_HOST = join(THIS_DIR, "server_wrong_host.cert")

CLIENT_KEY        = join(THIS_DIR, "client.key")
CLIENT_CERT       = join(THIS_DIR, "client.cert")
CLIENT_IP_CERT    = join(THIS_DIR, "client_ip.cert")
CLIENT_WILD_CERT  = join(THIS_DIR, "client_wildcard.cert")
CLIENT_WRONG_CA   = join(THIS_DIR, "client_wrong_ca.cert")
CLIENT_WRONG_HOST = join(THIS_DIR, "client_wrong_host.cert")

class Root:
    @cherrypy.expose
    def index(self):
        return "ok"

class HTTPSTests(object):
    regular_fail = False
    checked_fail = False
    server_host  = "localhost"
    client_host  = "localhost"
    server_ca    = CA_CERT
    server_cert  = SERVER_CERT
    client_cert  = CLIENT_CERT
    server_check = "ignore"     # ignore, optional, required
    server_ssl   = "builtin"    # builtin, pyopenssl
    server_check_host = True
    
    def setUp(self):
        socket.setdefaulttimeout(1)
        
        cherrypy.config.update({
            "checker.on": False,
            "log.screen": False,
            "engine.autoreload_on": False,
            
            "server.socket_host": self.server_host,
            "server.socket_port": 8080,
            
            "server.ssl_private_key":  SERVER_KEY,
            "server.ssl_certificate":  self.server_cert,
            "server.ssl_client_CA":    self.server_ca,
            "server.ssl_client_check": self.server_check,
            "server.ssl_module":       self.server_ssl,
            "server.ssl_client_check_host": self.server_check_host,
        })
        cherrypy.tree.mount(Root())
        cherrypy.engine.start()
        cherrypy.engine.wait(cherrypy.engine.states.STARTED)
        
        self.opener = urllib2.build_opener(VerifiedHTTPSHandler(
            ca_certs  = CA_CERT,
            key_file  = CLIENT_KEY,
            cert_file = self.client_cert
        ))
        
        self.url = "https://" + self.client_host + ":8080/"
    
    def tearDown(self):
        cherrypy.engine.exit()
        cherrypy.engine.wait(cherrypy.engine.states.EXITING)
        cherrypy.server.httpserver = None   # force the ssl adaptor to reload
    
    def test_checked(self):
        if self.checked_fail:
            self.assertRaises(Exception, self.opener.open, self.url)
        else:
            self.assertEqual("ok", self.opener.open(self.url).read())
    
    def test_regular(self):
        if self.regular_fail:
            self.assertRaises(urllib2.URLError, urllib2.urlopen, self.url)
        else:
            self.assertEqual("ok", urllib2.urlopen(self.url).read())


SSL_MODULES = ["builtin", "pyopenssl"]
BAD_SERVER_CERTS = [SERVER_WRONG_CA, SERVER_WRONG_HOST]
BAD_CLIENT_CERTS = [CLIENT_WRONG_CA, CLIENT_WRONG_HOST]
GOOD_CLIENT_CERTS = [CLIENT_CERT, CLIENT_IP_CERT, CLIENT_WILD_CERT]
SERVER_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]
if socket.getaddrinfo("localhost", 8080)[0][0] == socket.AF_INET6:
    CLIENT_HOSTS = ["localhost"]
else:
    CLIENT_HOSTS = ["localhost", "127.0.0.1"]

TESTS = [
    {"regular_fail": False,
     "checked_fail": False,
     "settings": {"server_check": ["ignore","optional"],
                  "client_cert": GOOD_CLIENT_CERTS}},
    {"regular_fail": False,
     "checked_fail": False,
     "settings": {"server_ca":    [None],
                  "server_check": ["ignore","optional","required"],
                  "client_cert":  GOOD_CLIENT_CERTS + BAD_CLIENT_CERTS}},
    {"regular_fail": False,
     "checked_fail": False,
     "settings": {"server_check": ["ignore"],
                  "client_cert":  GOOD_CLIENT_CERTS + BAD_CLIENT_CERTS}},
    {"regular_fail": True,
     "checked_fail": False,
     "settings": {"server_check": ["required"],
                  "client_cert": GOOD_CLIENT_CERTS}},
    {"regular_fail": True,
     "checked_fail": True,
     "settings": {"server_check": ["required"],
                  "client_cert": BAD_CLIENT_CERTS}},
    {"regular_fail": False,
     "checked_fail": True,
     "settings": {"server_check": ["optional"],
                  "client_cert": BAD_CLIENT_CERTS}},
    {"regular_fail": False,
     "checked_fail": True,
     "settings": {"server_check": ["ignore","optional"],
                  "server_cert": BAD_SERVER_CERTS}},
    {"regular_fail": True,
     "checked_fail": True,
     "settings": {"server_check": ["required"],
                  "server_cert": BAD_SERVER_CERTS}},
    {"regular_fail": True,
     "checked_fail": False,
     "settings": {"server_check": ["required"],
                  "client_cert": [CLIENT_WRONG_HOST],
                  "server_check_host": [False]}},
    {"regular_fail": False,
     "checked_fail": False,
     "settings": {"server_check": ["optional"],
                  "client_cert": [CLIENT_WRONG_HOST],
                  "server_check_host": [False]}},
]
for ssl_mod in SSL_MODULES:
    for client_host,server_host in itertools.product(CLIENT_HOSTS,SERVER_HOSTS):
        for tests in TESTS:
            combos = []
            for attr,vals in tests["settings"].items():
                combos.append([(attr,val) for val in vals])

            for settings in itertools.product(*combos):
                attrs = dict(settings, server_ssl   = ssl_mod,
                                       server_host  = server_host,
                                       client_host  = client_host,
                                       regular_fail = tests["regular_fail"],
                                       checked_fail = tests["checked_fail"])
                name = "SSLClientCertTest_" + str(attrs)
                globals()[name] = type(name, (HTTPSTests, TestCase), attrs)
