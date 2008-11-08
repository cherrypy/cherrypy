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

import os
thisdir = os.path.abspath(os.path.dirname(__file__))
import re
import sys
import thread
import time
import warnings

import cherrypy
from cherrypy.lib import http, profiler
from cherrypy.test import webtest


class CPWebCase(webtest.WebCase):
    
    script_name = ""
    scheme = "http"
    
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
    
    def tearDown(self):
        pass
    
    def getPage(self, url, headers=None, method="GET", body=None, protocol=None):
        """Open the url. Return status, headers, body."""
        if self.script_name:
            url = http.urljoin(self.script_name, url)
        return webtest.WebCase.getPage(self, url, headers, method, body, protocol)
    
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
            self._handlewebError('Error page does not match\n' + page)
            return
        
        # Now test the pattern against the traceback
        if pattern is None:
            # Special-case None to mean that there should be *no* traceback.
            if m and m.group(1):
                self._handlewebError('Error page contains traceback')
        else:
            if (m is None) or (not re.search(re.escape(pattern), m.group(1))):
                msg = 'Error page does not contain %s in traceback'
                self._handlewebError(msg % repr(pattern))


CPTestLoader = webtest.ReloadingTestLoader()
CPTestRunner = webtest.TerseTestRunner(verbosity=2)

def setConfig(conf):
    """Set the global config using a copy of conf."""
    if isinstance(conf, basestring):
        # assume it's a filename
        cherrypy.config.update(conf)
    else:
        cherrypy.config.update(conf.copy())


def run_test_suite(moduleNames, server, conf):
    """Run the given test modules using the given server and [global] conf.
    
    The server is started and stopped once, regardless of the number
    of test modules. The config, however, is reset for each module.
    """
    cherrypy.config.reset()
    setConfig(conf)
    engine = cherrypy.engine
    if hasattr(engine, "signal_handler"):
        engine.signal_handler.subscribe()
    if hasattr(engine, "console_control_handler"):
        engine.console_control_handler.subscribe()
    # The Pybots automatic testing system needs the suite to exit
    # with a non-zero value if there were any problems.
    # Might as well stick it in the engine... :/
    engine.test_success = True
    engine.start_with_callback(_run_test_suite_thread,
                               args=(moduleNames, conf))
    engine.block()
    if engine.test_success:
        return 0
    else:
        return 1

def sync_apps(profile=False, validate=False, conquer=False):
    app = cherrypy.tree
    if profile:
        app = profiler.make_app(app, aggregate=False)
    if conquer:
        try:
            import wsgiconq
        except ImportError:
            warnings.warn("Error importing wsgiconq. pyconquer will not run.")
        else:
            app = wsgiconq.WSGILogger(app)
    if validate:
        try:
            from wsgiref import validate
        except ImportError:
            warnings.warn("Error importing wsgiref. The validator will not run.")
        else:
            app = validate.validator(app)
    
    h = cherrypy.server.httpserver
    if hasattr(h, 'wsgi_app'):
        # CherryPy's wsgiserver
        h.wsgi_app = app
    elif hasattr(h, 'fcgiserver'):
        # flup's WSGIServer
        h.fcgiserver.application = app
    elif hasattr(h, 'scgiserver'):
        # flup's WSGIServer
        h.scgiserver.application = app

def _run_test_suite_thread(moduleNames, conf):
    try:
        for testmod in moduleNames:
            # Must run each module in a separate suite,
            # because each module uses/overwrites cherrypy globals.
            cherrypy.tree = cherrypy._cptree.Tree()
            cherrypy.config.reset()
            setConfig(conf)
            
            m = __import__(testmod, globals(), locals())
            setup = getattr(m, "setup_server", None)
            if setup:
                setup()
            
            # The setup functions probably mounted new apps.
            # Tell our server about them.
            sync_apps(profile=conf.get("profiling.on", False),
                      validate=conf.get("validator.on", False),
                      conquer=conf.get("conquer.on", False),
                      )
            
            suite = CPTestLoader.loadTestsFromName(testmod)
            result = CPTestRunner.run(suite)
            cherrypy.engine.test_success &= result.wasSuccessful()
            
            teardown = getattr(m, "teardown_server", None)
            if teardown:
                teardown()
    finally:
        cherrypy.engine.exit()

def testmain(conf=None):
    """Run __main__ as a test module, with webtest debugging."""
    engine = cherrypy.engine
    if '--server' in sys.argv:
        # Run the test module server-side only; wait for Ctrl-C to break.
        conf = conf or {}
        conf['server.socket_host'] = '0.0.0.0'
        setConfig(conf)
        if hasattr(engine, "signal_handler"):
            engine.signal_handler.subscribe()
        if hasattr(engine, "console_control_handler"):
            engine.console_control_handler.subscribe()
        engine.start()
        engine.block()
    else:
        for arg in sys.argv:
            if arg.startswith('--client='):
                # Run the test module client-side only.
                sys.argv.remove(arg)
                conf = conf or {}
                conf['server.socket_host'] = host = arg.split('=', 1)[1].strip()
                setConfig(conf)
                webtest.WebCase.HOST = host
                webtest.WebCase.PORT = cherrypy.server.socket_port
                webtest.main()
                break
        else:
            # Run normally (both server and client in same process).
            conf = conf or {}
            conf['server.socket_host'] = '127.0.0.1'
            setConfig(conf)
            engine.start_with_callback(_test_main_thread)
            engine.block()

def _test_main_thread():
    try:
        webtest.WebCase.PORT = cherrypy.server.socket_port
        webtest.main()
    finally:
        cherrypy.engine.exit()



# --------------------------- Spawning helpers --------------------------- #


class CPProcess(object):
    
    pid_file = os.path.join(thisdir, 'test.pid')
    config_file = os.path.join(thisdir, 'test.conf')
    config_template = """[global]
server.socket_host: '%(host)s'
server.socket_port: %(port)s
log.screen: False
log.error_file: r'%(error_log)s'
log.access_file: r'%(access_log)s'
%(ssl)s
%(extra)s
"""
    error_log = os.path.join(thisdir, 'test.error.log')
    access_log = os.path.join(thisdir, 'test.access.log')
    
    def __init__(self, wait=False, daemonize=False, ssl=False):
        self.wait = wait
        self.daemonize = daemonize
        self.ssl = ssl
        self.host = cherrypy.server.socket_host
        self.port = cherrypy.server.socket_port
    
    def write_conf(self, extra=""):
        if self.ssl:
            serverpem = os.path.join(thisdir, 'test.pem')
            ssl = """
server.ssl_certificate: r'%s'
server.ssl_private_key: r'%s'
""" % (serverpem, serverpem)
        else:
            ssl = ""
        
        f = open(self.config_file, 'wb')
        f.write(self.config_template %
                {'host': self.host,
                 'port': self.port,
                 'error_log': self.error_log,
                 'access_log': self.access_log,
                 'ssl': ssl,
                 'extra': extra,
                 })
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

