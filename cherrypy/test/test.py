"""
Copyright (c) 2004, CherryPy Team (team@cherrypy.org)
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, 
are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice, 
      this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice, 
      this list of conditions and the following disclaimer in the documentation 
      and/or other materials provided with the distribution.
    * Neither the name of the CherryPy Team nor the names of its contributors 
      may be used to endorse or promote products derived from this software 
      without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND 
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED 
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE 
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE 
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL 
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR 
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER 
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, 
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE 
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import sys
import os, os.path
import webtest
import getopt


class TestHarness(object):
    
    """A test harness for the CherryPy framework and CherryPy applications."""
    
    # The first server in the list is the default server.
    available_servers = {'serverless': (0, "Serverless", None),
                         'native': (1, "Native HTTP Server",
                                    "cherrypy._cphttpserver.embedded_server"),
                         'wsgi': (2, "Native WSGI Server",
                                  "cherrypy._cpwsgi.WSGIServer"),
                         }
    default_server = "wsgi"
    
    def __init__(self, available_tests):
        """Constructor to populate the TestHarness instance.
        
        available_tests should be a list of module names (strings).
        """
        self.available_tests = available_tests
        
        self.cover = False
        self.profile = False
        self.protocol = "HTTP/1.0"
        self.basedir = None
        
        self.servers = []
        self.tests = []
    
    def load(self, args=sys.argv[1:]):
        """Populate a TestHarness from sys.argv.
        
        args defaults to sys.argv[1:], but you can provide a different
            set of args if you like.
        """
        
        longopts = ['cover', 'profile', '1.1', 'help', 'basedir=', 'all']
        longopts.extend(self.available_servers)
        longopts.extend(self.available_tests)
        try:
            opts, args = getopt.getopt(args, "", longopts)
        except getopt.GetoptError:
            # print help information and exit
            self.help()
            sys.exit(2)
        
        self.cover = False
        self.profile = False
        self.protocol = "HTTP/1.0"
        self.basedir = None
        
        self.servers = []
        self.tests = []
        
        for o, a in opts:
            if o == '--help':
                self.help()
                sys.exit()
            elif o == "--cover":
                self.cover = True
            elif o == "--profile":
                self.profile = True
            elif o == "--1.1":
                self.protocol = "HTTP/1.1"
            elif o == "--basedir":
                self.basedir = a
            elif o == "--all":
                self.servers = self.available_servers.keys()
            else:
                o = o[2:]
                if o in self.available_servers and o not in self.servers:
                    self.servers.append(o)
                elif o in self.available_tests and o not in self.tests:
                    self.tests.append(o)
        
        if self.cover and self.profile:
            # Print error message and exit
            print ('Error: you cannot run the profiler and the '
                   'coverage tool at the same time.')
            sys.exit(2)
        
        if not self.servers:
            self.servers = [self.default_server]
        
        if not self.tests:
            self.tests = self.available_tests[:]
    
    def help(self):
        """Print help for test.py command-line options."""
        
        print """CherryPy Test Program
    Usage:
        test.py --servers* --1.1 --cover --basedir=path --profile --tests**
        
    """
        print '    * servers:'
        s = [(val, name) for name, val in self.available_servers.iteritems()]
        s.sort()
        for val, name in s:
            if name == self.default_server:
                print '        --' + name, '(default)'
            else:
                print '        --' + name
        
        print """        --all (runs all servers in order)
    
    --1.1: use HTTP/1.1 servers instead of default HTTP/1.0
    
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
        self.load()
        
        # Start the coverage tool before importing cherrypy,
        # so module-level global statements are covered.
        if self.cover:
            self.start_coverage()
        
        import cherrypy
        print "Python version used to run this test script:", sys.version.split()[0]
        print "CherryPy version", cherrypy.__version__
        print
        
        if conf is None:
            conf = {'server.socketHost': '127.0.0.1',
                    'server.socketPort': 8000,
                    'server.threadPool': 10,
                    'server.logToScreen': False,
                    'server.environment': "production",
                    'server.showTracebacks': True,
                    }
        elif isinstance(conf, basestring):
            conf = cherrypy.config.dict_from_config_file(conf)
        
        conf['server.protocolVersion'] = self.protocol
        
        if self.profile:
            conf['profiling.on'] = True
        
        self._run_all_servers(conf)
        
        if self.profile:
            del conf['profiling.on']
            print
            print ("run /cherrypy/lib/profiler.py as a script to serve "
                   "profiling results on port 8080")
        
        if self.cover:
            self.stop_coverage()
    
    def _run_all_servers(self, conf):
        # helper must be imported lazily so the coverage tool
        # can run against module-level statements within cherrypy.
        from cherrypy.test import helper
        s = [self.available_servers[name] for name in self.servers]
        s.sort()
        for priority, name, cls in s:
            print
            print "Running tests:", name
            helper.run_test_suite(self.tests, cls, conf)


class CPTestHarness(TestHarness):
    
    def _run_all_servers(self, conf):
        from cherrypy.test import helper
        
        class NotReadyTest(helper.CPWebCase):
            def testNotReadyError(self):
                # Without having called "cherrypy.server.start()", we should
                # get a NotReady error
                class Root: pass
                import cherrypy
                cherrypy.root = Root()
                self.assertRaises(cherrypy.NotReady, self.getPage, "/")
        helper.CPTestRunner.run(NotReadyTest("testNotReadyError"))
        
        TestHarness._run_all_servers(self, conf)


if __name__ == '__main__':
    
    # Place this __file__'s grandparent (../../) at the start of sys.path,
    # so that all cherrypy/* imports are from this __file__'s package.
    localDir = os.path.dirname(__file__)
    curpath = os.path.normpath(os.path.join(os.getcwd(), localDir))
    sys.path.insert(0, os.path.normpath(os.path.join(curpath, '../../')))
    
    testList = [
        'test_baseurl_filter',
        'test_cache_filter',
        'test_combinedfilters',
        'test_core',
        'test_decodingencoding_filter',
        'test_gzip_filter',
        'test_logdebuginfo_filter',
        'test_objectmapping',
        'test_static_filter',
        'test_tutorials',
        'test_virtualhost_filter',
        'test_session_filter',
    ]
    CPTestHarness(testList).run()
    
    print
    raw_input('hit enter')
