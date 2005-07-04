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

import time
import sys
import os, os.path
import unittest


class CPTestResult(unittest._TextTestResult):
    def printErrors(self):
        # Overridden to avoid unnecessary empty line
        if self.errors or self.failures:
            if self.dots or self.showAll:
                self.stream.writeln()
            self.printErrorList('ERROR', self.errors)
            self.printErrorList('FAIL', self.failures)


class CPTestRunner(unittest.TextTestRunner):
    """A test runner class that displays results in textual form."""
    
    def _makeResult(self):
        return CPTestResult(self.stream, self.descriptions, self.verbosity)
    
    def run(self, test):
        "Run the given test case or test suite."
        # Overridden to remove unnecessary empty lines and separators
        result = self._makeResult()
        startTime = time.time()
        test(result)
        timeTaken = float(time.time() - startTime)
        result.printErrors()
        if not result.wasSuccessful():
            self.stream.write("FAILED (")
            failed, errored = map(len, (result.failures, result.errors))
            if failed:
                self.stream.write("failures=%d" % failed)
            if errored:
                if failed: self.stream.write(", ")
                self.stream.write("errors=%d" % errored)
            self.stream.writeln(")")
        return result


class ReloadingTestLoader(unittest.TestLoader):
    
    def loadTestsFromName(self, name, module=None):
        """Return a suite of all tests cases given a string specifier.

        The name may resolve either to a module, a test case class, a
        test method within a test case class, or a callable object which
        returns a TestCase or TestSuite instance.

        The method optionally resolves the names relative to a given module.
        """
        parts = name.split('.')
        if module is None:
            if not parts:
                raise ValueError, "incomplete test name: %s" % name
            else:
                parts_copy = parts[:]
                while parts_copy:
                    target = ".".join(parts_copy)
                    if target in sys.modules:
                        module = reload(sys.modules[target])
                        break
                    else:
                        try:
                            module = __import__(target)
                            break
                        except ImportError:
                            del parts_copy[-1]
                            if not parts_copy: raise
                parts = parts[1:]
        obj = module
        for part in parts:
            obj = getattr(obj, part)
        
        import unittest
        import types
        if type(obj) == types.ModuleType:
            return self.loadTestsFromModule(obj)
        elif (isinstance(obj, (type, types.ClassType)) and
              issubclass(obj, unittest.TestCase)):
            return self.loadTestsFromTestCase(obj)
        elif type(obj) == types.UnboundMethodType:
            return obj.im_class(obj.__name__)
        elif callable(obj):
            test = obj()
            if not isinstance(test, unittest.TestCase) and \
               not isinstance(test, unittest.TestSuite):
                raise ValueError, \
                      "calling %s returned %s, not a test" % (obj,test)
            return test
        else:
            raise ValueError, "don't know how to make test from: %s" % obj

CPTestLoader = ReloadingTestLoader()


def main():
    # Place our current directory's parent (cherrypy/) at the beginning
    # of sys.path, so that all imports are from our current directory.
    localDir = os.path.dirname(__file__)
    curpath = os.path.normpath(os.path.join(os.getcwd(), localDir))
    sys.path.insert(0, os.path.normpath(os.path.join(curpath, '../../')))
    
    print "Python version used to run this test script:", sys.version.split()[0]
    try:
        import cherrypy
    except ImportError:
        print "Error: couldn't find CherryPy !"
        os._exit(-1)
    print "CherryPy version", cherrypy.__version__
    print
    
    import cherrypy
    from cherrypy.test import helper
    
    class NotReadyTest(unittest.TestCase):
        def testNotReadyError(self):
            # Without having called "cherrypy.server.start()", we should
            # get a NotReady error
            self.assertRaises(cherrypy.NotReady, helper.request, "/")
    CPTestRunner(verbosity=2).run(NotReadyTest("testNotReadyError"))
    
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
    ]
    
    server_conf = {'server.socketHost': helper.HOST,
                   'server.socketPort': helper.PORT,
                   'server.threadPool': 10,
                   'server.logToScreen': False,
                   'server.environment': "production",
                   'profiling.on': True,
                   }
    
    for name, server in [("Serverless", None),
                         ("Native HTTP Server", "cherrypy._cphttpserver.embedded_server"),
                         ("Native WSGI Server", "cherrypy._cpwsgi.WSGIServer"),
                         ]:
        print
        print "Running tests:", name
        
        cherrypy.config.update({'global': server_conf.copy()})
        helper.startServer(server)
        for testmod in testList:
            # Must run each module in a separate suite,
            # because each module uses/overwrites cherrypy globals.
            cherrypy.config.reset()
            cherrypy.config.update({'global': server_conf.copy()})
            suite = CPTestLoader.loadTestsFromName(testmod)
            CPTestRunner(verbosity=2).run(suite)
        helper.stopServer()
    
    raw_input('hit enter')

if __name__ == '__main__':
    main()
