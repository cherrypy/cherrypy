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

import cherrypy


class Root:
    def index(self):
        return "Hello World"
    index.exposed = True
    
    def ctrlc(self):
        raise KeyboardInterrupt()
    ctrlc.exposed = True

cherrypy.root = Root()
cherrypy.config.update({
    'global': {
        'server.logToScreen': False,
        'server.environment': 'production',
    },
})


import helper

class ServerStateTests(helper.CPWebCase):
    
    def test_0_NormalStateFlow(self):
        # Without having called "cherrypy.server.start()", we should
        # get a NotReady error
        self.assertRaises(cherrypy.NotReady, self.getPage, "/")
        
        # Test server start
        helper.startServer(self.serverClass)
        self.assertEqual(cherrypy._appserver_state, 1)
        
        if self.serverClass:
            host = cherrypy.config.get('server.socketHost')
            port = cherrypy.config.get('server.socketPort')
            self.assertRaises(IOError, cherrypy.server.check_port, host, port)
        
        self.getPage("/")
        self.assertBody("Hello World")
        
        # Test server stop
        helper.stopServer()
        self.assertEqual(cherrypy._appserver_state, 0)
        
        # Once the server has stopped, we should get a NotReady error again.
        self.assertRaises(cherrypy.NotReady, self.getPage, "/")
    
    def test_1_KeyboardInterrupts(self):
        if self.serverClass:
            # Raise a keyboard interrupt in the HTTP server's main thread.
            
            def raiser(x=None):
                raise KeyboardInterrupt
            
            helper.startServer(self.serverClass)
            
            name = cherrypy._httpserver.__class__.__name__
            if name == "WSGIServer":
                cherrypy._httpserver.tick = raiser
            elif name in ("CherryHTTPServer", "PooledThreadServer"):
                cherrypy._httpserver.handle_request = raiser
            else:
                raise ValueError("Unknown HTTP server: %s" % name)
            
            # Give the server time to shut down.
            while cherrypy._appserver_state != 0:
                time.sleep(.1)
            self.assertEqual(cherrypy._httpserver, None)
            
            # Once the server has stopped, we should get a NotReady error again.
            self.assertRaises(cherrypy.NotReady, self.getPage, "/")
    
    def test_2_Restart(self):
        # Test server start
        import cherrypy
        
        helper.startServer(self.serverClass)
        self.getPage("/")
        self.assertBody("Hello World")
        
        # Test server restart
        cherrypy.server.restart()
        
        self.assertEqual(cherrypy._appserver_state, 1)
        self.getPage("/")
        self.assertBody("Hello World")


def run(server, conf):
    helper.setConfig(conf)
    cherrypy._cputil._cpInitDefaultFilters()
    ServerStateTests.serverClass = server
    suite = helper.CPTestLoader.loadTestsFromTestCase(ServerStateTests)
    try:
        helper.CPTestRunner.run(suite)
    finally:
        helper.stopServer()


if __name__ == "__main__":
    conf = {'server.socketHost': '127.0.0.1',
            'server.socketPort': 8000,
            'server.threadPool': 10,
            'server.logToScreen': False,
            'server.logConfigOptions': False,
            'server.environment': "production",
            'server.showTracebacks': True,
            }
    def _run(server):
        print
        print "Testing %s..." % (server or "serverless")
        run(server, conf)
    _run(None)
    _run("cherrypy._cpwsgi.WSGIServer")
    _run("cherrypy._cphttpserver.PooledThreadServer")
    conf['server.threadPool'] = 1
    _run("cherrypy._cphttpserver.CherryHTTPServer")

