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

import os, os.path
import time
import socket
import StringIO
import threading

import cherrypy
import webtest
import types
for _x in dir(cherrypy):
    y = getattr(cherrypy, _x)
    if isinstance(y, types.ClassType) and issubclass(y, cherrypy.Error):
        webtest.ignored_exceptions.append(y)

HOST = "127.0.0.1"
PORT = 8000


def port_is_free():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((HOST, PORT))
        s.close()
        return False
    except socket.error:
        return True


def startServer(serverClass=None):
    if serverClass is None:
        cherrypy.server.start(initOnly=True)
    else:
        if not port_is_free():
            raise IOError("Port %s is in use; perhaps the previous server "
                          "did not shut down properly." % PORT)
        t = threading.Thread(target=cherrypy.server.start, args=(False, serverClass))
        t.start()
        time.sleep(1)


def stopServer():
    cherrypy.server.stop()
    if cherrypy.config.get('server.threadPool') > 1:
        # With thread-pools, it can take up to 1 sec for the server to stop
        time.sleep(1.1)


def onerror():
    handled = webtest.server_error()
    if not handled:
        cherrypy._cputil._cpOnError()


class CPWebCase(webtest.WebCase):
    
    def getPage(self, url, headers=None, method="GET", body=None):
        # Install a custom error handler, so errors in the server will:
        # 1) show server tracebacks in the test output, and
        # 2) stop the HTTP request (if any) and ignore further assertions.
        cherrypy.root._cpOnError = onerror
        
        resp = cherrypy.response
        if cherrypy._httpserver is None:
            requestLine = "%s %s HTTP/1.0" % (method.upper(), url)
            headers = webtest.cleanHeaders(headers, method, body)
            
            found = False
            for k, v in headers:
                if k.lower() == 'host':
                    found = True
                    break
            if not found:
                headers.append(("Host", "%s:%s" % (HOST, PORT)))
            
            if body is not None:
                body = StringIO.StringIO(body)
            
            cherrypy.server.request(HOST, HOST, requestLine, headers, body, "http")
            resp.body = "".join([chunk for chunk in resp.body])
            if webtest.ServerError.on:
                raise webtest.ServerError
        else:
            result = webtest.WebCase.getPage(self, url, headers, method, body)
            resp.status, resp.headerMap, resp.body = result
            # We want both .headerMap and .headers to be available.
            resp.headers = [(k, v) for k, v in resp.headerMap.iteritems()]

