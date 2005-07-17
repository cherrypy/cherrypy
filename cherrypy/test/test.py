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


testDict = {
    'baseurlFilter'          : 'test_baseurl_filter',
    'cacheFilter'            : 'test_cache_filter',
    'combinedFilters'        : 'test_combinedfilters',
    'core'                   : 'test_core',
    'decodingEncodingFilter' : 'test_decodingencoding_filter',
    'gzipFilter'             : 'test_gzip_filter',
    'logDebugInfoFilter'     : 'test_logdebuginfo_filter',
    'objectMapping'          : 'test_objectmapping',
    'staticFilter'           : 'test_static_filter',
    'tutorials'              : 'test_tutorials',
    'virtualHostFilter'      : 'test_virtualhost_filter',
##    'sessionFilter'          : 'test_session_filter'
}


def help():
    print """CherryPy Test Program
    Usage: 
        test.py -mode testName1 testName2 testName...
    
    modes: wsgi, severless, native, all
      default: wsgi
    """
    
    print '    tests:'
    for testString in testDict:
        print '        ', testString


class BadArgument(Exception):
    pass

class DisplayHelp(Exception):
    pass


def getOptions(args):
    
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
    argSet.difference_update(['-wsgi', '-native', '-serverless', '-all'])
    
    cover = ("-cover" in argSet)
    profile = ("-profile" in argSet)
    if cover and profile:
        raise BadArgument('Bad Arguments: you cannot run the profiler and the coverage tool at the same time.')
    argSet.difference_update(['-cover', '-profile'])
    
    tests = []
    for testString, test in testDict.iteritems():
        if testString.lower() in argSet:
            tests.append(testDict[testString])
            argSet.discard(testString.lower())
    if not tests:
        tests = testDict.values()
    
    if len(argSet):
        for arg in args:
            if arg.lower() in argSet:
                raise BadArgument('Bad Argument: %s is not a valid option.' % arg)
    return (servers, tests, cover, profile)


def main(servers, testList, cover=False, profile=False):
    # Place our current directory's parent (cherrypy/) at the beginning
    # of sys.path, so that all imports are from our current directory.
    localDir = os.path.dirname(__file__)
    curpath = os.path.normpath(os.path.join(os.getcwd(), localDir))
    sys.path.insert(0, os.path.normpath(os.path.join(curpath, '../../')))
    
    if cover:
        # Start the coverage tool before importing cherrypy,
        # so module-level global statements are covered.
        try:
            from coverage import the_coverage as coverage
            coverage.cache_default = c = os.path.join(os.path.dirname(__file__),
                                                      "../lib/coverage.cache")
            if c and os.path.exists(c):
                os.remove(c)
            coverage.start()
        except ImportError:
            coverage = None
    
    import cherrypy
    print "Python version used to run this test script:", sys.version.split()[0]
    print "CherryPy version", cherrypy.__version__
    print
    
    from cherrypy.test import helper
    
    class NotReadyTest(helper.CPWebCase):
        def testNotReadyError(self):
            # Without having called "cherrypy.server.start()", we should
            # get a NotReady error
            class Root: pass
            cherrypy.root = Root()
            self.assertRaises(cherrypy.NotReady, self.getPage, "/")
    helper.CPTestRunner.run(NotReadyTest("testNotReadyError"))
    
    server_conf = {'global': {'server.socketHost': helper.HOST,
                              'server.socketPort': helper.PORT,
                              'server.threadPool': 10,
                              'server.logToScreen': False,
                              'server.environment': "production",
                              }
                   }
    
    if cover:
        cherrypy.codecoverage = True
    
    if profile:
        server_conf['profiling.on'] = True
    
    if 'serverless' in servers:
        print
        print "Running testList: Serverless"
        helper.run_test_suite(testList, None, server_conf)
    
    if 'native' in servers:
        print
        print "Running testList: Native HTTP Server"
        helper.run_test_suite(testList, "cherrypy._cphttpserver.embedded_server", server_conf)
    
    if 'wsgi' in servers:
        print
        print "Running testList: Native WSGI Server"
        helper.run_test_suite(testList, "cherrypy._cpwsgi.WSGIServer", server_conf)
    
    if profile or cover:
        print
    
    if profile:
        del server_conf['profiling.on']
        print "run /cherrypy/lib/profiler.py as a script to serve profiling results on port 8080"
    
    if cover:
        cherrypy.codecoverage = False
        if coverage:
            coverage.save()
            helper.report_coverage(coverage)
            print "run /cherrypy/lib/covercp.py as a script to serve coverage results on port 8080"
    
    print
    raw_input('hit enter')


if __name__ == '__main__':
    try:
        servers, testList, cover, profile = getOptions(sys.argv[1:])
    except DisplayHelp:
        help()
    except BadArgument, argError:
        print argError
    else:
        main(servers, testList, cover, profile)
