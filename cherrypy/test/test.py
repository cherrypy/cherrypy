"""The actual script that runs the entire CP test suite.

There is a library of helper functions for the CherryPy test suite,
called "helper.py" (in this folder); this module calls that as a library.
"""

# GREAT CARE has been taken to separate this module from helper.py,
# because different consumers of each have mutually-exclusive import
# requirements. So don't go moving functions from here into helper.py,
# or vice-versa, unless you *really* know what you're doing.


import getopt
import httplib
import os
localDir = os.path.dirname(__file__)
serverpem = os.path.join(os.getcwd(), localDir, 'test.pem')
import sys


class TestHarness(object):
    """A test harness for the CherryPy framework and CherryPy applications."""
    
    def __init__(self, tests=None, server=None, protocol="HTTP/1.1",
                 port=8000, scheme="http", interactive=True, host='127.0.0.1'):
        """Constructor to populate the TestHarness instance.
        
        tests should be a list of module names (strings).
        """
        self.tests = tests or []
        self.server = server
        self.protocol = protocol
        self.port = port
        self.host = host
        self.scheme = scheme
        self.interactive = interactive
    
    def run(self, conf=None):
        """Run the test harness (using the given [global] conf)."""
        import cherrypy
        v = sys.version.split()[0]
        print "Python version used to run this test script:", v
        print "CherryPy version", cherrypy.__version__
        if self.scheme == "https":
            ssl = "(ssl)"
        else:
            ssl = ""
        print "HTTP server version", self.protocol, ssl
        print "PID:", os.getpid()
        print
        
        # Override these in _run as needed:
        cherrypy.server.using_wsgi = True
        cherrypy.server.using_apache = False
        
        if isinstance(conf, basestring):
            parser = cherrypy.config._Parser()
            conf = parser.dict_from_file(conf).get('global', {})
        else:
            conf = conf or {}
        baseconf = conf.copy()
        baseconf.update({'server.socket_host': self.host,
                         'server.socket_port': self.port,
                         'server.protocol_version': self.protocol,
                         'environment': "test_suite",
                         })
        if self.scheme == "https":
            baseconf['server.ssl_certificate'] = serverpem
            baseconf['server.ssl_private_key'] = serverpem
        return self._run(baseconf)
    
    def _run(self, conf):
        # helper must be imported lazily so the coverage tool
        # can run against module-level statements within cherrypy.
        # Also, we have to do "from cherrypy.test import helper",
        # exactly like each test module does, because a relative import
        # would stick a second instance of webtest in sys.modules,
        # and we wouldn't be able to globally override the port anymore.
        from cherrypy.test import helper, webtest
        webtest.WebCase.PORT = self.port
        webtest.WebCase.HOST = self.host
        webtest.WebCase.harness = self
        helper.CPWebCase.scheme = self.scheme
        webtest.WebCase.interactive = self.interactive
        if self.scheme == "https":
            webtest.WebCase.HTTP_CONN = httplib.HTTPSConnection
        print
        print "Running tests:", self.server
        return helper.run_test_suite(self.tests, self.server, conf)


class CommandLineParser(object):
    available_servers = {'wsgi': "cherrypy._cpwsgi.CPWSGIServer",
                         'cpmodpy': "cpmodpy",
                         'modpygw': "modpygw",
                         'modwsgi': "modwsgi",
                         'modfcgid': "modfcgid",
                         }
    default_server = "wsgi"
    scheme = "http"
    protocol = "HTTP/1.1"
    port = 8080
    host = '127.0.0.1'
    cover = False
    profile = False
    validate = False
    conquer = False
    server = None
    basedir = None
    interactive = True
    
    shortopts = []
    longopts = ['cover', 'profile', 'validate', 'conquer', 'dumb', '1.0',
                'ssl', 'help', 'basedir=', 'port=', 'server=', 'host=']
    
    def __init__(self, available_tests, args=sys.argv[1:]):
        """Constructor to populate the TestHarness instance.
        
        available_tests should be a list of module names (strings).
        
        args defaults to sys.argv[1:], but you can provide a different
            set of args if you like.
        """
        self.available_tests = available_tests
        
        longopts = self.longopts[:]
        longopts.extend(self.available_tests)
        try:
            opts, args = getopt.getopt(args, self.shortopts, longopts)
        except getopt.GetoptError:
            # print help information and exit
            self.help()
            sys.exit(2)
        
        self.tests = []
        
        for o, a in opts:
            if o == '--help':
                self.help()
                sys.exit()
            elif o == "--cover":
                self.cover = True
            elif o == "--profile":
                self.profile = True
            elif o == "--validate":
                self.validate = True
            elif o == "--conquer":
                self.conquer = True
            elif o == "--dumb":
                self.interactive = False
            elif o == "--1.0":
                self.protocol = "HTTP/1.0"
            elif o == "--ssl":
                self.scheme = "https"
            elif o == "--basedir":
                self.basedir = a
            elif o == "--port":
                self.port = int(a)
            elif o == "--host":
                self.host = a
            elif o == "--server":
                if a in self.available_servers:
                    a = self.available_servers[a]
                self.server = a
            else:
                o = o[2:]
                if o in self.available_tests and o not in self.tests:
                    self.tests.append(o)
        
        if self.cover and self.profile:
            # Print error message and exit
            print ('Error: you cannot run the profiler and the '
                   'coverage tool at the same time.')
            sys.exit(2)
        
        if not self.server:
            self.server = self.available_servers[self.default_server]
        
        if not self.tests:
            self.tests = self.available_tests[:]
    
    def help(self):
        """Print help for test.py command-line options."""
        
        print """CherryPy Test Program
    Usage:
        test.py --help --server=* --host=%s --port=%s --1.0 --ssl --cover
            --basedir=path --profile --validate --conquer --dumb --tests**
        
    """ % (self.__class__.host, self.__class__.port)
        print '    * servers:'
        for name, val in self.available_servers.iteritems():
            if name == self.default_server:
                print '        --server=%s: %s (default)' % (name, val)
            else:
                print '        --server=%s: %s' % (name, val)
        
        print """
    
    --host=<name or IP addr>: use a host other than the default (%s).
        Not yet available with mod_python servers.
    --port=<int>: use a port other than the default (%s)
    --1.0: use HTTP/1.0 servers instead of default HTTP/1.1
    
    --cover: turn on code-coverage tool
    --basedir=path: display coverage stats for some path other than cherrypy.
    
    --profile: turn on profiling tool
    --validate: use wsgiref.validate (builtin in Python 2.5).
    --conquer: use wsgiconq (which uses pyconquer) to trace calls.
    --dumb: turn off the interactive output features.
    """ % (self.__class__.host, self.__class__.port)
        
        print '    ** tests:'
        for name in self.available_tests:
            print '        --' + name
    
    def start_coverage(self):
        """Start the coverage tool.
        
        To use this feature, you need to download 'coverage.py',
        either Gareth Rees' original implementation:
        http://www.garethrees.org/2001/12/04/python-coverage/
        
        or Ned Batchelder's enhanced version:
        http://www.nedbatchelder.com/code/modules/coverage.html
        
        If neither module is found in PYTHONPATH,
        coverage is silently(!) disabled.
        """
        try:
            from coverage import the_coverage as coverage
            c = os.path.join(os.path.dirname(__file__), "../lib/coverage.cache")
            coverage.cache_default = c
            if c and os.path.exists(c):
                os.remove(c)
            coverage.start()
            import cherrypy
            from cherrypy.lib import covercp
            cherrypy.engine.subscribe('start', covercp.start)
            cherrypy.engine.subscribe('start_thread', covercp.start)
        except ImportError:
            coverage = None
        self.coverage = coverage
    
    def stop_coverage(self):
        """Stop the coverage tool, save results, and report."""
        import cherrypy
        from cherrypy.lib import covercp
        cherrypy.engine.unsubscribe('start', covercp.start)
        cherrypy.engine.unsubscribe('start_thread', covercp.start)
        if self.coverage:
            self.coverage.save()
            self.report_coverage()
            print ("run cherrypy/lib/covercp.py as a script to serve "
                   "coverage results on port 8080")
    
    def report_coverage(self):
        """Print a summary from the code coverage tool."""
        
        basedir = self.basedir
        if basedir is None:
            # Assume we want to cover everything in "../../cherrypy/"
            basedir = os.path.normpath(os.path.join(os.getcwd(), localDir, '../'))
        else:
            if not os.path.isabs(basedir):
                basedir = os.path.normpath(os.path.join(os.getcwd(), basedir))
        basedir = basedir.lower()
        
        self.coverage.get_ready()
        morfs = [x for x in self.coverage.cexecuted
                 if x.lower().startswith(basedir)]
        
        total_statements = 0
        total_executed = 0
        
        print
        print "CODE COVERAGE (this might take a while)",
        for morf in morfs:
            sys.stdout.write(".")
            sys.stdout.flush()
##            name = os.path.split(morf)[1]
            if morf.find('test') != -1:
                continue
            try:
                _, statements, _, missing, readable  = self.coverage.analysis2(morf)
                n = len(statements)
                m = n - len(missing)
                total_statements = total_statements + n
                total_executed = total_executed + m
            except KeyboardInterrupt:
                raise
            except:
                # No, really! We truly want to ignore any other errors.
                pass
        
        pc = 100.0
        if total_statements > 0:
            pc = 100.0 * total_executed / total_statements
        
        print ("\nTotal: %s Covered: %s Percent: %2d%%"
               % (total_statements, total_executed, pc))
    
    def run(self, conf=None):
        """Run the test harness (using the given [global] conf)."""
        conf = conf or {}
        
        # Start the coverage tool before importing cherrypy,
        # so module-level global statements are covered.
        if self.cover:
            self.start_coverage()
        
        if self.profile:
            conf['profiling.on'] = True
        
        if self.validate:
            conf['validator.on'] = True
        
        if self.conquer:
            conf['conquer.on'] = True
        
        if self.server == 'cpmodpy':
            from cherrypy.test import modpy
            h = modpy.ModPythonTestHarness(self.tests, self.server,
                                           self.protocol, self.port,
                                           "http", self.interactive)
            h.use_wsgi = False
        elif self.server == 'modpygw':
            from cherrypy.test import modpy
            h = modpy.ModPythonTestHarness(self.tests, self.server,
                                           self.protocol, self.port,
                                           "http", self.interactive)
            h.use_wsgi = True
        elif self.server == 'modwsgi':
            from cherrypy.test import modwsgi
            h = modwsgi.ModWSGITestHarness(self.tests, self.server,
                                           self.protocol, self.port,
                                           "http", self.interactive)
            h.use_wsgi = True
        elif self.server == 'modfcgid':
            from cherrypy.test import modfcgid
            h = modfcgid.FCGITestHarness(self.tests, self.server,
                                         self.protocol, self.port,
                                         "http", self.interactive)
        else:
            h = TestHarness(self.tests, self.server, self.protocol,
                            self.port, self.scheme, self.interactive,
                            self.host)
        
        success = h.run(conf)
        
        if self.profile:
            print
            print ("run /cherrypy/lib/profiler.py as a script to serve "
                   "profiling results on port 8080")
        
        if self.cover:
            self.stop_coverage()
        
        return success


def prefer_parent_path():
    # Place this __file__'s grandparent (../../) at the start of sys.path,
    # so that all cherrypy/* imports are from this __file__'s package.
    curpath = os.path.normpath(os.path.join(os.getcwd(), localDir))
    grandparent = os.path.normpath(os.path.join(curpath, '../../'))
    if grandparent not in sys.path:
        sys.path.insert(0, grandparent)

def run():
    
    prefer_parent_path()
    
    testList = [
        'test_proxy',
        'test_caching',
        'test_config',
##        'test_conn',
        'test_core',
        'test_tools',
        'test_encoding',
        'test_etags',
        'test_http',
        'test_httpauth',
        'test_httplib',
        'test_logging',
        'test_objectmapping',
        'test_misc_tools',
        'test_static',
        'test_tutorials',
        'test_virtualhost',
        'test_safe_multipart',
        'test_session',
        'test_sessionauthenticate',
##        'test_states',
        'test_tidy',
        'test_xmlrpc',
        'test_wsgiapps',
        'test_wsgi_ns',
        'test_wsgi_vhost',
        
        # Run refleak test as late as possible to
        # catch refleaks from all exercised tests.
        'test_refleaks',
    ]
    
    try:
        import routes
        testList.append('test_routes')
    except ImportError:
        pass
    
    clp = CommandLineParser(testList)
    success = clp.run()
    if clp.interactive:
        print
        raw_input('hit enter')
    sys.exit(success)


if __name__ == '__main__':
    run()
