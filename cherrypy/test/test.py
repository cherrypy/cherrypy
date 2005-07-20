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

try:
    set
except NameError:
    from sets import Set as set


def help(testList):
    """Print help for test.py command-line options."""
    
    print """CherryPy Test Program
    Usage: 
        test.py -mode -cover -profile -1.1 testName1 testName2 testName...
    
    modes: wsgi, severless, native, all (default is wsgi)
    
    cover: turns on code-coverage tool
    
    profile: turns on profiling tool
    
    1.1: use HTTP/1.1 servers instead of default HTTP/1.0
    """
    
    print '    tests:'
    for name in testList:
        print '        ', name


class BadArgument(Exception):
    pass

class DisplayHelp(Exception):
    pass


class Options:
    
    """A container for test.py command-line options."""
    
    def __init__(self, args, testList):
        """Constructor to populate the Options instance.
        
        args is usually sys.argv[1:].
        testList should be a list of module names (strings).
        """
        
        argSet = set([arg.lower() for arg in args])
        
        if '-help' in args:
            raise DisplayHelp
        
        servers = set()
        if '-all' in argSet:
            servers.update(['wsgi', 'native', 'serverless'])
        else:
            if '-native' in argSet:
                servers.add('native')
            if '-serverless' in argSet:
                servers.add('serverless')
            if '-wsgi' in argSet or not servers:
                servers.add('wsgi')
        self.servers = servers
        argSet.difference_update(['-wsgi', '-native', '-serverless', '-all'])
        
        self.cover = ("-cover" in argSet)
        self.profile = ("-profile" in argSet)
        if self.cover and self.profile:
            raise BadArgument('Bad Arguments: you cannot run the profiler and the coverage tool at the same time.')
        argSet.difference_update(['-cover', '-profile'])
        
        if "-1.1" in argSet:
            self.protocol = "HTTP/1.1"
            argSet.difference_update(['-1.1'])
        else:
            self.protocol = "HTTP/1.0"
        
        # All remaining args should be test names.
        tests = []
        for name in testList:
            if ("-" + name) in argSet:
                tests.append(name)
                argSet.discard("-" + name)
        if not tests:
            tests = testList
        self.tests = tests
        
        if len(argSet):
            for arg in args:
                if arg.lower() in argSet:
                    raise BadArgument('Bad Argument: %s is not a valid option.' % arg)

def get_coverage():
    """Return a coverage.the_coverage instance.
    
    To use this feature, or the coverage server in cherrypy/lib/covercp,
    you need to download 'coverage.py', either Gareth Rees' original
    implementation:
    http://www.garethrees.org/2001/12/04/python-coverage/
    
    or Ned Batchelder's enhanced version:
    http://www.nedbatchelder.com/code/modules/coverage.html
    
    If neither module is found in PYTHONPATH, this module returns None.
    """
    try:
        from coverage import the_coverage as coverage
        c = os.path.join(os.path.dirname(__file__), "../lib/coverage.cache")
        coverage.cache_default = c
        if c and os.path.exists(c):
            os.remove(c)
        coverage.start()
    except ImportError:
        coverage = None
    return coverage


def main(opts, conf=None, includeNotReady=False):
    """Run the test suite against multiple servers and other options.
    
    opts should be an Options instance, with the following attributes:
        tests = a list of module names
        servers = a list of servers (serverless, wsgi, native, all)
        cover = whether or not to run the coverage tool
        profile = whether or not to run the profiling tool
        protocol = the HTTP protocol version for requests, e.g. "HTTP/1.0"
    
    conf may be a dictionary or a filename (string).
    
    includeNotReady specifies whether or not to run the NotReadyTest,
        (which is typically only run for cherrypy itself; other apps
        which use this module may safely leave it off/False).
    
    """
    
    if opts.cover:
        # Start the coverage tool before importing cherrypy,
        # so module-level global statements are covered.
        coverage = get_coverage()
    
    import cherrypy
    print "Python version used to run this test script:", sys.version.split()[0]
    print "CherryPy version", cherrypy.__version__
    print
    
    from cherrypy.test import helper
    
    if includeNotReady:
        class NotReadyTest(helper.CPWebCase):
            def testNotReadyError(self):
                # Without having called "cherrypy.server.start()", we should
                # get a NotReady error
                class Root: pass
                cherrypy.root = Root()
                self.assertRaises(cherrypy.NotReady, self.getPage, "/")
        helper.CPTestRunner.run(NotReadyTest("testNotReadyError"))
    
    if conf is None:
        conf = {'global': {'server.socketHost': helper.HOST,
                           'server.socketPort': helper.PORT,
                           'server.threadPool': 10,
                           'server.logToScreen': False,
                           'server.environment': "production",
                           }
                }
    elif isinstance(conf, basestring):
        conf = cherrypy.config.dict_from_config_file(conf)
    
    conf['server.protocolVersion'] = opts.protocol
    
    if opts.cover:
        cherrypy.codecoverage = True
    
    if opts.profile:
        conf['profiling.on'] = True
    
    if 'serverless' in opts.servers:
        print
        print "Running tests: Serverless"
        helper.run_test_suite(opts.tests, None, conf)
    
    if 'native' in opts.servers:
        print
        print "Running tests: Native HTTP Server"
        helper.run_test_suite(opts.tests,
                              "cherrypy._cphttpserver.embedded_server",
                              conf)
    
    if 'wsgi' in opts.servers:
        print
        print "Running tests: Native WSGI Server"
        helper.run_test_suite(opts.tests,
                              "cherrypy._cpwsgi.WSGIServer",
                              conf)
    
    if opts.profile or opts.cover:
        print
    
    if opts.profile:
        del conf['profiling.on']
        print "run /cherrypy/lib/profiler.py as a script to serve profiling results on port 8080"
    
    if opts.cover:
        cherrypy.codecoverage = False
        if coverage:
            coverage.save()
            helper.report_coverage(coverage)
            print "run /cherrypy/lib/covercp.py as a script to serve coverage results on port 8080"


if __name__ == '__main__':
    
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
##        'test_session_filter',
    ]
    
    try:
        opts = Options(sys.argv[1:], testList)
    except DisplayHelp:
        help(testList)
    except BadArgument, argError:
        print argError
    else:
        # Place our current directory's parent (cherrypy/) at the beginning
        # of sys.path, so that all imports are from our current directory.
        localDir = os.path.dirname(__file__)
        curpath = os.path.normpath(os.path.join(os.getcwd(), localDir))
        sys.path.insert(0, os.path.normpath(os.path.join(curpath, '../../')))
        
        main(opts, includeNotReady=True)
    
    print
    raw_input('hit enter')
