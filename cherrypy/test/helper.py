"""A library of helper functions for the CherryPy test suite.

The actual script that runs the entire CP test suite is called
"test.py" (in this folder); test.py calls this module as a library.

Usage
=====
Each individual test_*.py module imports this module (helper),
usually to make an instance of CPWebCase, and then call testmain().

The CP test suite script (test.py) imports this module and calls
run_test_suite, possibly more than once. CP applications may also
import test.py (to use TestHarness), which then calls helper.py.
"""

# GREAT CARE has been taken to separate this module from test.py,
# because different consumers of each have mutually-exclusive import
# requirements. So don't go moving functions from here into test.py,
# or vice-versa, unless you *really* know what you're doing.

import datetime
import os
thisdir = os.path.abspath(os.path.dirname(__file__))
import re
import sys
import time
import warnings

import cherrypy
from cherrypy.lib import httputil, profiler
from cherrypy.test import test, webtest

import logging
log = logging.getLogger(__name__)

class CPWebCase(webtest.WebCase):
    script_name = ""
    scheme = "http"

    available_servers = {'wsgi': test.LocalWSGISupervisor,
                         'wsgi_u': test.get_wsgi_u_supervisor,
                         'native': test.NativeServerSupervisor,
                         'cpmodpy': test.get_cpmodpy_supervisor,
                         'modpygw': test.get_modpygw_supervisor,
                         'modwsgi': test.get_modwsgi_supervisor,
                         'modfcgid': test.get_modfcgid_supervisor,
                         }
    default_server = "wsgi"
    supervisor_factory = None

    @classmethod
    def _setup_server(cls, supervisor, conf):
        v = sys.version.split()[0]
        log.info("Python version used to run this test script: %s" % v)
        log.info("CherryPy version: %s" % cherrypy.__version__)
        if supervisor.scheme == "https":
            ssl = " (ssl)"
        else:
            ssl = ""
        log.info("HTTP server version: %s%s" % (supervisor.protocol, ssl))
        log.info("PID: %s" % os.getpid())

        cherrypy.server.using_apache = supervisor.using_apache
        cherrypy.server.using_wsgi = supervisor.using_wsgi

        if isinstance(conf, basestring):
            parser = cherrypy.lib.reprconf.Parser()
            conf = parser.dict_from_file(conf).get('global', {})
        else:
            conf = conf or {}
        baseconf = conf.copy()
        baseconf.update({'server.socket_host': supervisor.host,
                         'server.socket_port': supervisor.port,
                         'server.protocol_version': supervisor.protocol,
                         'environment': "test_suite",
                         })
        if supervisor.scheme == "https":
            baseconf['server.ssl_certificate'] = serverpem
            baseconf['server.ssl_private_key'] = serverpem

        # helper must be imported lazily so the coverage tool
        # can run against module-level statements within cherrypy.
        # Also, we have to do "from cherrypy.test import helper",
        # exactly like each test module does, because a relative import
        # would stick a second instance of webtest in sys.modules,
        # and we wouldn't be able to globally override the port anymore.
        if supervisor.scheme == "https":
            webtest.WebCase.HTTP_CONN = HTTPSConnection
        return baseconf

    @classmethod
    def setup_class(cls):
        ''
        #Creates a server
        conf = test.get_tst_config()
        if not cls.supervisor_factory:
            cls.supervisor_factory = cls.available_servers.get(conf.get('server', 'wsgi'))
            if cls.supervisor_factory is None:
                raise RuntimeError('Unknown server in config: %s' % conf['server'])
        supervisor = cls.supervisor_factory(**conf)

        #Copied from "run_test_suite"
        cherrypy.config.reset()
        baseconf = cls._setup_server(supervisor, conf)
        cherrypy.config.update(baseconf)
        setup_client()

        if hasattr(cls, 'setup_server'):
            # Clear the cherrypy tree and clear the wsgi server so that
            # it can be updated with the new root
            cherrypy.tree = cherrypy._cptree.Tree()
            cherrypy.server.httpserver = None
            cls.setup_server()
            supervisor.start(cls.__module__)

        cls.supervisor = supervisor


    @classmethod
    def teardown_class(cls):
        ''
        if hasattr(cls, 'setup_server'):
            cls.supervisor.stop()

    def prefix(self):
        return self.script_name.rstrip("/")

    def base(self):
        if ((self.scheme == "http" and self.PORT == 80) or
            (self.scheme == "https" and self.PORT == 443)):
            port = ""
        else:
            port = ":%s" % self.PORT

        return "%s://%s%s%s" % (self.scheme, self.HOST, port,
                                self.script_name.rstrip("/"))

    def exit(self):
        sys.exit()

    def getPage(self, url, headers=None, method="GET", body=None, protocol=None):
        """Open the url. Return status, headers, body."""
        if self.script_name:
            url = httputil.urljoin(self.script_name, url)
        return webtest.WebCase.getPage(self, url, headers, method, body, protocol)

    def skip(self, msg='skipped '):
        sys.stderr.write(msg)

    def assertErrorPage(self, status, message=None, pattern=''):
        """Compare the response body with a built in error page.

        The function will optionally look for the regexp pattern,
        within the exception embedded in the error page."""

        # This will never contain a traceback
        page = cherrypy._cperror.get_error_page(status, message=message)

        # First, test the response body without checking the traceback.
        # Stick a match-all group (.*) in to grab the traceback.
        esc = re.escape
        epage = esc(page)
        epage = epage.replace(esc('<pre id="traceback"></pre>'),
                              esc('<pre id="traceback">') + '(.*)' + esc('</pre>'))
        m = re.match(epage, self.body, re.DOTALL)
        if not m:
            self._handlewebError('Error page does not match; expected:\n' + page)
            return

        # Now test the pattern against the traceback
        if pattern is None:
            # Special-case None to mean that there should be *no* traceback.
            if m and m.group(1):
                self._handlewebError('Error page contains traceback')
        else:
            if (m is None) or (
                not re.search(re.escape(pattern),
                              m.group(1))):
                msg = 'Error page does not contain %s in traceback'
                self._handlewebError(msg % repr(pattern))

    date_tolerance = 2

    def assertEqualDates(self, dt1, dt2, seconds=None):
        """Assert abs(dt1 - dt2) is within Y seconds."""
        if seconds is None:
            seconds = self.date_tolerance

        if dt1 > dt2:
            diff = dt1 - dt2
        else:
            diff = dt2 - dt1
        if not diff < datetime.timedelta(seconds=seconds):
            raise AssertionError('%r and %r are not within %r seconds.' %
                                 (dt1, dt2, seconds))


def setup_client():
    """Set up the WebCase classes to match the server's socket settings."""
    webtest.WebCase.PORT = cherrypy.server.socket_port
    webtest.WebCase.HOST = cherrypy.server.socket_host
    if cherrypy.server.ssl_certificate:
        CPWebCase.scheme = 'https'

# --------------------------- Spawning helpers --------------------------- #


class CPProcess(object):

    pid_file = os.path.join(thisdir, 'test.pid')
    config_file = os.path.join(thisdir, 'test.conf')
    config_template = """[global]
server.socket_host: '%(host)s'
server.socket_port: %(port)s
checker.on: False
log.screen: False
log.error_file: r'%(error_log)s'
log.access_file: r'%(access_log)s'
%(ssl)s
%(extra)s
"""
    error_log = os.path.join(thisdir, 'test.error.log')
    access_log = os.path.join(thisdir, 'test.access.log')

    def __init__(self, wait=False, daemonize=False, ssl=False, socket_host=None, socket_port=None):
        self.wait = wait
        self.daemonize = daemonize
        self.ssl = ssl
        self.host = socket_host or cherrypy.server.socket_host
        self.port = socket_port or cherrypy.server.socket_port

    def write_conf(self, extra=""):
        if self.ssl:
            serverpem = os.path.join(thisdir, 'test.pem')
            ssl = """
server.ssl_certificate: r'%s'
server.ssl_private_key: r'%s'
""" % (serverpem, serverpem)
        else:
            ssl = ""

        conf = self.config_template % {
            'host': self.host,
            'port': self.port,
            'error_log': self.error_log,
            'access_log': self.access_log,
            'ssl': ssl,
            'extra': extra,
            }
        f = open(self.config_file, 'wb')
        f.write(conf)
        f.close()

    def start(self, imports=None):
        """Start cherryd in a subprocess."""
        cherrypy._cpserver.wait_for_free_port(self.host, self.port)

        args = [sys.executable, os.path.join(thisdir, '..', 'cherryd'),
                '-c', self.config_file, '-p', self.pid_file]

        if not isinstance(imports, (list, tuple)):
            imports = [imports]
        for i in imports:
            if i:
                args.append('-i')
                args.append(i)

        if self.daemonize:
            args.append('-d')

        if self.wait:
            self.exit_code = os.spawnl(os.P_WAIT, sys.executable, *args)
        else:
            os.spawnl(os.P_NOWAIT, sys.executable, *args)
            cherrypy._cpserver.wait_for_occupied_port(self.host, self.port)

        # Give the engine a wee bit more time to finish STARTING
        if self.daemonize:
            time.sleep(2)
        else:
            time.sleep(1)

    def get_pid(self):
        return int(open(self.pid_file, 'rb').read())

    def join(self):
        """Wait for the process to exit."""
        try:
            try:
                # Mac, UNIX
                os.wait()
            except AttributeError:
                # Windows
                try:
                    pid = self.get_pid()
                except IOError:
                    # Assume the subprocess deleted the pidfile on shutdown.
                    pass
                else:
                    os.waitpid(pid, 0)
        except OSError, x:
            if x.args != (10, 'No child processes'):
                raise

