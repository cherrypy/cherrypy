"""
Copyright (c) 2005, CherryPy Team (team@cherrypy.org)
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

"""
A WSGI application and server (see PEP 333).
"""

import threading
import os, socket, sys, traceback, urllib
import SocketServer, BaseHTTPServer
import cpg, _cpserver, _cputil, _cphttptools


def requestLine(environ):
    # Rebuild first line of the request
    resource = environ.get('SCRIPT_NAME', '') + environ.get('PATH_INFO', '')
    qString = environ.get('QUERY_STRING')
    if qString:
        resource += '?' + qString
    return ('%s %s %s' % (environ['REQUEST_METHOD'],
                          resource or '/',
                          environ['SERVER_PROTOCOL']
                          )
            )

headerNames = {'HTTP_CGI_AUTHORIZATION': 'Authorization',
               'CONTENT_LENGTH': 'Content-Length',
               'CONTENT_TYPE': 'Content-Type',
               'REMOTE_HOST': 'Remote-Host',
               'REMOTE_ADDR': 'Remote-Addr',
               }

def translate_headers(environ):
    for cgiName in environ:
        translatedHeader = headerNames.get(cgiName.upper())
        if translatedHeader:
            yield translatedHeader, environ[cgiName]
        elif cgiName.upper().startswith("HTTP_"):
            # Hackish attempt at recovering original header names.
            translatedHeader = cgiName[5:].replace("_", "-")
            yield translatedHeader, environ[cgiName]

class NullWriter(object):
    
    def write(self, data):
        pass


def wsgiApp(environ, start_response):
    
    # Trap screen output from BaseHTTPRequestHandler.log_message()
    if not cpg.config.get('server.logToScreen'):
        sys.stderr = NullWriter()
    
    try:
        cpg.request.method = environ['REQUEST_METHOD']
        cpg.request.multithread = environ['wsgi.multithread']
        cpg.request.multiprocess = environ['wsgi.multiprocess']
        r = _cpserver.request(environ['REMOTE_ADDR'],
                              environ['REMOTE_ADDR'],
                              requestLine(environ),
                              translate_headers(environ),
                              environ['wsgi.input'],
                              )
        start_response(cpg.response.status, cpg.response.headers)
        for chunk in cpg.response.body:
            # WSGI requires all data to be of type "str". This coercion should
            # not take any time at all if chunk is already of type "str".
            # If it's unicode, it could be a big performance hit (x ~500).
            yield str(chunk)
    except:
        tb = _cphttptools.formatExc()
        _cputil.getSpecialFunction('_cpLogMessage')(tb)
        s, h, b = _cphttptools.bareError(tb)
        start_response(s, h, sys.exc_info())
        for chunk in b:
            yield str(chunk)



# Server components

class WSGIRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    
    server_version = "CherryPyWSGI/2.1"
    os_environ = dict(os.environ.items())
    
    def handle_one_request(self):
        """Handle a single HTTP request. Overridden to handle all verbs."""
        response = None
        self.headers_sent = False
        self.responseHeaders = []
        try:
            try:
                self.raw_requestline = self.rfile.readline()
                if not self.raw_requestline:
                    self.close_connection = 1
                    return
                
                if not self.parse_request():
                    return
                
                response = wsgiApp(self.environ(), self.start_response)
                for chunk in response:
                    self.write(chunk)
            except:
                self.handleError(sys.exc_info())
        finally:
            if hasattr(response, 'close'):
                response.close()
    
    def environ(self):
        env = {'wsgi.version': (1, 0),
               'wsgi.input': self.rfile,
               'wsgi.errors': sys.stderr,
               'wsgi.multithread': (cpg.config.get("server.threadPool") > 1),
               'wsgi.multiprocess': False,
               'wsgi.run_once': False,
               'SERVER_PROTOCOL': self.request_version,
               'GATEWAY_INTERFACE': 'CGI/1.1',
               'CONTENT_TYPE': self.headers.get('Content-Type', ''),
               'CONTENT_LENGTH': self.headers.get('Content-Length', ''),
               # SCRIPT_NAME doesn't really apply to CherryPy
               'SCRIPT_NAME': '',
               }
        
        env['SERVER_NAME'] = cpg.config.get('server.socketHost')
        env['SERVER_PORT'] = cpg.config.get('server.socketPort')
        
        if self.os_environ.get("HTTPS") in ('yes', 'on', '1'):
            env['wsgi.url_scheme'] = 'https'
        else:
            env['wsgi.url_scheme'] = 'http'
        
        host, port = self.client_address[:2]
        env['REMOTE_ADDR'] = host
        
        fullhost = socket.getfqdn(host)
        if fullhost == host:
            env['REMOTE_HOST'] = ''
        else:
            env['REMOTE_HOST'] = fullhost
        
        # Update env with results of parse_request
        env['REQUEST_METHOD'] = self.command
        env['SERVER_PROTOCOL'] = self.request_version
        
        if '?' in self.path:
            path, query = self.path.split('?', 1)
        else:
            path, query = self.path, ''
        env['PATH_INFO'] = urllib.unquote(path)
        env['QUERY_STRING'] = query
        
        # Update env with additional request headers
        for name, value in self.headers.items():
            env['HTTP_%s' % name.replace ('-', '_').upper()] = value
        return env
    
    def start_response(self, status, headers, exc_info=None):
        if exc_info:
            try:
                if self.headers_sent:
                    raise exc_info[0], exc_info[1], exc_info[2]
            finally:
                # avoid dangling circular ref
                exc_info = None
        elif self.responseHeaders:
            raise AssertionError("Headers already set!")
        self.status = status
        self.responseHeaders = headers[:]
        return self.write
    
    def write(self, data):
        if not self.headers_sent:
            code, reason = self.status.split(" ", 1)
            self.send_response(int(code), reason)
            for name, value in self.responseHeaders:
                self.send_header(name, value)
            self.end_headers()
            self.headers_sent = True
        self.wfile.write(data)
    
    def send_response(self, code, message=None):
        self.log_request(code)
        if message is None:
            if code in self.responses:
                message = self.responses[code][0]
            else:
                message = ''
        if self.request_version != 'HTTP/0.9':
            self.wfile.write("%s %d %s\r\n" %
                             (self.protocol_version, code, message))
    
    def handleError(self, exc):
        self.close_connection = 1
        msg = _cphttptools.formatExc(exc)
        _cputil.getSpecialFunction('_cpLogMessage')(msg, "HTTP")
        self.status, self.headers, body = _cphttptools.bareError()
        self.write(body)


def WSGIServer():
    import _cphttpserver
    return _cphttpserver.embedded_server(WSGIRequestHandler)
