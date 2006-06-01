"""The actual script that runs the entire CP test suite.

There is a library of helper functions for the CherryPy test suite,
called "helper.py" (in this folder); this module calls that as a library.
"""

# GREAT CARE has been taken to separate this module from helper.py,
# because different consumers of each have mutually-exclusive import
# requirements. So don't go moving functions from here into helper.py,
# or vice-versa, unless you *really* know what you're doing.


import sys
import os, os.path
import webtest
import getopt


class TestHarness(object):
    """A test harness for the CherryPy framework and CherryPy applications."""
    
    def __init__(self, tests=None, server=None, protocol="HTTP/1.1", port=8000):
        """Constructor to populate the TestHarness instance.
        
        tests should be a list of module names (strings).
        """
        self.protocol = protocol
        self.port = port
        self.server = server
        self.tests = tests or []
    
    def run(self, conf=None):
        """Run the test harness."""
        import cherrypy
        v = sys.version.split()[0]
        print "Python version used to run this test script:", v
        print "CherryPy version", cherrypy.__version__
        print
        
        if isinstance(conf, basestring):
            conf = cherrypy.config.dict_from_config_file(conf)
        baseconf = {'server.socket_host': '127.0.0.1',
                    'server.socket_port': self.port,
                    'server.thread_pool': 10,
                    'log_to_screen': False,
                    'environment': "production",
                    'show_tracebacks': True,
                    }
        baseconf.update(conf or {})
        
        baseconf['server.protocol_version'] = self.protocol
        self._run(baseconf)
    
    def _run(self, conf):
        # helper must be imported lazily so the coverage tool
        # can run against module-level statements within cherrypy.
        # Also, we have to do a relative import here, not
        # "from cherrypy.test import helper", because the latter
        # would stick a second instance of webtest in sys.modules,
        # and we wouldn't be able to globally override the port anymore.
        import helper
        webtest.WebCase.PORT = self.port
        print
        print "Running tests:", self.server
        helper.run_test_suite(self.tests, self.server, conf)


class CommandLineParser(object):
    available_servers = {'wsgi': "cherrypy._cpwsgi.WSGIServer",
                         'modpy': "modpy",
                         }
    default_server = "wsgi"
    
    def __init__(self, available_tests, args=sys.argv[1:]):
        """Constructor to populate the TestHarness instance.
        
        available_tests should be a list of module names (strings).
        
        args defaults to sys.argv[1:], but you can provide a different
            set of args if you like.
        """
        self.available_tests = available_tests
        self.cover = False
        self.profile = False
        self.server = None
        self.port = 8080
        self.protocol = "HTTP/1.1"
        
        longopts = ['cover', 'profile', '1.1', 'help', 'basedir=', 'port=',
                    'server=']
        longopts.extend(self.available_servers)
        longopts.extend(self.available_tests)
        try:
            opts, args = getopt.getopt(args, "", longopts)
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
            elif o == "--1.0":
                self.protocol = "HTTP/1.0"
            elif o == "--basedir":
                self.basedir = a
            elif o == "--port":
                self.port = int(a)
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
        test.py --server=* --1.0 --cover --basedir=path --profile --tests**
        
    """
        print '    * servers:'
        for name, val in self.available_servers.iteritems():
            if name == self.default_server:
                print '        --%s: %s (default)' % (name, val)
            else:
                print '        --%s: %s' % (name, val)
        
        print """
    
    --1.0: use HTTP/1.0 servers instead of default HTTP/1.1
    
    --cover: turn on code-coverage tool
    --basedir=path: display coverage stats for some path other than cherrypy.
    
    --profile: turn on profiling tool
    """
        
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
        
        If neither module is found in PYTHONPATH, coverage is disabled.
        """
        try:
            from coverage import the_coverage as coverage
            c = os.path.join(os.path.dirname(__file__), "../lib/coverage.cache")
            coverage.cache_default = c
            if c and os.path.exists(c):
                os.remove(c)
            coverage.start()
            import cherrypy
            cherrypy.codecoverage = True
        except ImportError:
            coverage = None
        self.coverage = coverage
    
    def stop_coverage(self):
        """Stop the coverage tool, save results, and report."""
        import cherrypy
        cherrypy.codecoverage = False
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
            localDir = os.path.dirname(__file__)
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
            name = os.path.split(morf)[1]
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
        """Run the test harness."""
        # Start the coverage tool before importing cherrypy,
        # so module-level global statements are covered.
        if self.cover:
            self.start_coverage()
        
        if self.profile:
            conf = conf or {}
            conf['profiling.on'] = True
        
        if self.server == 'modpy':
            import modpy
            modpy.ModPythonTestHarness(self.tests, self.server,
                                       self.protocol, self.port).run(conf)
        else:
            TestHarness(self.tests, self.server,
                        self.protocol, self.port).run(conf)
        
        if self.profile:
            del conf['profiling.on']
            print
            print ("run /cherrypy/lib/profiler.py as a script to serve "
                   "profiling results on port 8080")
        
        if self.cover:
            self.stop_coverage()


def prefer_parent_path():
    # Place this __file__'s grandparent (../../) at the start of sys.path,
    # so that all cherrypy/* imports are from this __file__'s package.
    localDir = os.path.dirname(__file__)
    curpath = os.path.normpath(os.path.join(os.getcwd(), localDir))
    grandparent = os.path.normpath(os.path.join(curpath, '../../'))
    if grandparent not in sys.path:
        sys.path.insert(0, grandparent)

def run():
    
    prefer_parent_path()
    
    testList = [
        'test_baseurl',
        'test_caching',
        'test_config',
        'test_core',
        'test_tools',
        'test_decodingencoding',
        'test_gzip',
        'test_objectmapping',
        'test_response_headers',
        'test_static',
        'test_tutorials',
        'test_virtualhost',
        'test_session',
        'test_sessionauthenticate',
##        'test_states',
        'test_xmlrpc',
        'test_wsgiapp',
    ]
    CommandLineParser(testList).run()
    
    print
    raw_input('hit enter')


if __name__ == '__main__':
    run()
