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

# This is a library of helper functions for the CherryPy test suite.
# The actual script that runs the entire CP test suite is called
# "test.py" (in this folder); test.py calls this module as a library.
# 
# GREAT CARE has been taken to separate this module from test.py,
# because different consumers of each have mutually-exclusive import
# requirements. So don't go moving functions from here into test.py,
# or vice-versa, unless you *really* know what you're doing.
# 
# Usage:
#   Each individual test_*.py module imports this module (helper),
#   usually to make an instance of CPWebCase, and then call testmain().
#   
#   The CP test suite script (test.py) imports this module and calls
#   run_test_suite, possibly more than once. CP applications may also
#   import test.py (to use TestHarness), which then calls helper.py.


import os, os.path
import re
import socket
import StringIO
import sys
import thread
import threading
import time
import types

import cherrypy
import webtest

for _x in dir(cherrypy):
    y = getattr(cherrypy, _x)
    if isinstance(y, types.ClassType) and issubclass(y, cherrypy.Error):
        webtest.ignored_exceptions.append(y)


def onerror():
    """Assign to _cpOnError to enable webtest server-side debugging."""
    handled = webtest.server_error()
    if not handled:
        cherrypy._cputil._cpOnError()


class VirtualRootFilter:
    
    def __init__(self, prefix):
        self.prefix = prefix
    
    def onStartResource(self):
        path = cherrypy.request.path
        if path.startswith(self.prefix):
            cherrypy.request.objectPath = path[len(self.prefix):]
vroot = ""
test_vrf = VirtualRootFilter(vroot)


class CPWebCase(webtest.WebCase):
    
    def exit(self):
        sys.exit()
    
    def _getRequest(self, url, headers, method, body):
        # Like getPage, but for serverless requests.
        webtest.ServerError.on = False
        self.url = url
        
        requestLine = "%s %s HTTP/1.1" % (method.upper(), url)
        headers = webtest.cleanHeaders(headers, method, body,
                                       self.HOST, self.PORT)
        if body is not None:
            body = StringIO.StringIO(body)
        
        request = cherrypy.server.request((self.HOST, self.PORT), self.HOST, "http")
        response = request.run(requestLine, headers, body)
        
        self.status = response.status
        self.headers = response.headers
        
        # Build a list of request cookies from the previous response cookies.
        self.cookies = [('Cookie', v) for k, v in self.headers
                        if k.lower() == 'set-cookie']
        
        try:
            self.body = []
            for chunk in response.body:
                self.body.append(chunk)
        except:
            if cherrypy.config.get("streamResponse", False):
                # Pass the error through
                raise
            
            from cherrypy import _cputil
            s, h, b = _cputil.bareError()
            # Don't reset status or headers; we're emulating an error which
            # occurs after status and headers have been written to the client.
            for chunk in b:
                self.body.append(chunk)
        self.body = "".join(self.body)
        
        if webtest.ServerError.on:
            self.tearDown()
            raise webtest.ServerError()
    
    def tearDown(self):
        pass
    
    def getPage(self, url, headers=None, method="GET", body=None):
        """Open the url with debugging support. Return status, headers, body."""
        # Install a custom error handler, so errors in the server will:
        # 1) show server tracebacks in the test output, and
        # 2) stop the HTTP request (if any) and ignore further assertions.
        cherrypy.root._cpOnError = onerror
        
        if vroot:
            url = vroot + url
            filters = getattr(cherrypy.root, "_cpFilterList", None)
            if filters is None:
                cherrypy.root._cpFilterList = filters = []
            if test_vrf not in filters:
                filters.append(test_vrf)
        
        if cherrypy.server.httpserver is None:
            self._getRequest(url, headers, method, body)
        else:
            webtest.WebCase.getPage(self, url, headers, method, body)
    
    def assertErrorPage(self, status, message=None, pattern=''):
        """ Compare the response body with a built in error page.
            The function will optionally look for the regexp pattern, 
            within the exception embedded in the error page.
        """
        
        from cherrypy._cputil import getErrorPage
        esc = re.escape
        # This will never contain a traceback:
        page = esc(getErrorPage(status, message=message))
        
        # First, test the response body without checking the traceback.
        # Stick a match-all group (.*) in to grab the traceback.
        page = page.replace(esc('<pre id="traceback"></pre>'),
                            esc('<pre id="traceback">') + '(.*)' + esc('</pre>'))
        m = re.match(page, self.body, re.DOTALL)
        if not m:
            self._handlewebError('Error page does not match\n' + page)
            return
        
        # Now test the pattern against the traceback
        if pattern is None:
            # Special-case None to mean that there should be *no* traceback.
            if m and m.group(1):
                self._handlewebError('Error page contains traceback')
        else:
            if (m is None) or (not re.search(pattern, m.group(1))):
                msg = 'Error page does not contain %s in traceback'
                self._handlewebError(msg % repr(pattern))


CPTestLoader = webtest.ReloadingTestLoader()
CPTestRunner = webtest.TerseTestRunner(verbosity=2)

def setConfig(conf):
    """Set the config using a copy of conf."""
    if isinstance(conf, basestring):
        # assume it's a filename
        cherrypy.config.update(file=conf)
    else:
        cherrypy.config.update(conf.copy())


def run_test_suite(moduleNames, server, conf):
    """Run the given test modules using the given server and conf.
    
    The server is started and stopped once, regardless of the number
    of test modules. The config, however, is reset for each module.
    """
    setConfig(conf)
    cherrypy.server.start_with_callback(_run_test_suite_thread,
                                        args=(moduleNames, conf),
                                        serverClass=server)

def _run_test_suite_thread(moduleNames, conf):
    cherrypy.server.wait()
    for testmod in moduleNames:
        # Must run each module in a separate suite,
        # because each module uses/overwrites cherrypy globals.
        cherrypy.config.reset()
        setConfig(conf)
        cherrypy._cputil._cpInitDefaultFilters()
        
        suite = CPTestLoader.loadTestsFromName(testmod)
        CPTestRunner.run(suite)
    thread.interrupt_main()

def testmain(server=None, conf=None):
    """Run __main__ as a test module, with webtest debugging."""
    if conf is None:
        conf = {}
    setConfig(conf)
    cherrypy.server.start_with_callback(_test_main_thread, serverClass=server)

def _test_main_thread():
    cherrypy.server.wait()
    cherrypy._cputil._cpInitDefaultFilters()
    try:
        webtest.main()
    finally:
        thread.interrupt_main()

