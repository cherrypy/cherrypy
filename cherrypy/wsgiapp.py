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

"""
WSGI interface for CherryPy
"""

import StringIO
import thread
from cherrypy import cpg, _cphttptools, _cpserver

def init(*a, **kw):
    kw['initOnly'] = 1
    _cpserver.start(*a, **kw)


def requestLine(environ):
    # Rebuild first line of the request
    resource = environ.get('SCRIPT_NAME', '') + environ.get('PATH_INFO', '')
    qString = environ.get('QUERY_STRING')
    if qString:
        resource += '?' + qString
    return ('%s %s %s' % (environ['REQUEST_METHOD'],
                          resource or '/',
                          environ['SERVER_PROTOCOL']
                          ))


headerNames = {'HTTP_HOST': 'Host',
               'HTTP_USER_AGENT': 'User-Agent',
               'HTTP_CGI_AUTHORIZATION': 'Authorization',
               'CONTENT_LENGTH': 'Content-Length',
               'CONTENT_TYPE': 'Content-Type',
               'HTTP_COOKIE': 'Cookie',
               'REMOTE_HOST': 'Remote-Host',
               'REMOTE_ADDR': 'Remote-Addr',
               'HTTP_REFERER': 'Referer',
               'HTTP_ACCEPT_ENCODING': 'Accept-Encoding',
               }

class wsgiHeaders(object):
    
    def __init__(self, environ):
        self.data = []
        for cgiName in environ:
            translatedHeader = headerNames.get(cgiName.upper())
            if translatedHeader:
                self.data.append((translatedHeader, environ[cgiName]))
    
    def items(self):
        return self.data
    
    def getallmatchingheaders(self, name):
        name = name.lower()
        for key, value in self.data:
            if key.lower() == name:
                yield "%s: %s" % (key, value)


class WSGIWriter(object):
    """wfile proxy for WSGI, using the 'write callable' hack."""
    
    def __init__(self, start_response):
        self.start_response = start_response
        self.buf = StringIO.StringIO()
        self.write_body = None
        self.closed = False
    
    def flush(self):
        if self.closed:
            raise ValueError("The output stream has been closed.")
    
    def close(self):
        # Note that we do not call .close() on the write_body callable.
        # That is specifically denied by PEP 333.
        self.closed = True
    
    def clean_status(self, line):
        status = line[len("HTTP/1.0 "):]
        
        # WSGI requires a Reason-phrase. Provide one if missing.
        try:
            code, reason = status.split(" ", 1)
            reason = reason.strip()
        except ValueError:
            code, reason = status, ""
        code = code.strip()
        assert code.isdigit()
        if not reason:
            reason = 'CherryPy'
        status = " ".join((code, reason))
        return status
    
    def write(self, data):
        if self.closed:
            raise ValueError("The output stream has been closed.")
        
        # WSGI requires all data to be of type "str". This coercion should
        # not take any time at all if data is already of type "str".
        # If it's unicode, it could be a big performance hit (x ~500).
        data = str(data)
        
        if self.write_body is None:
            # We haven't finished the headers yet.
            self.buf.write(data)
            buffer = self.buf.getvalue()
            end_of_headers = buffer.find("\r\n\r\n")
            if end_of_headers != -1:
                # Reached the end of headers.
                # Separate, process, and send the headers.
                headers = buffer[:end_of_headers]
                buffer = buffer[end_of_headers + 4:]
                
                headers = headers.split("\r\n")
                status = self.clean_status(headers.pop(0))
                
                # Notice we're not handling multiline headers.
                # AFAICT, CherryPy doesn't write any, and PEP 333
                # specifically denies them.
                headers = [tuple(line.split(": ", 1)) for line in headers]
                
                # Use the "write callable" hack described in PEP 333.
                # If CherryPy ever moves to "generators all the way down",
                # then we can avoid this hack.
                self.write_body = self.start_response(status, headers)
                if buffer:
                    self.write_body(buffer)
        else:
            self.write_body(data)


seen_threads = {}

def wsgiApp(environ, start_response):
    
    try:
        threadID = thread.get_ident()
        if threadID not in seen_threads:
            # Call the functions from cpg.server.onStartThreadList
            seen_threads[threadID] = None
            for func in cpg.server.onStartThreadList:
                func(len(seen_threads))
        
        cpg.request.method = environ['REQUEST_METHOD']
        
        _cphttptools.doRequest(environ['REMOTE_ADDR'],
                               environ['REMOTE_ADDR'],
                               requestLine(environ),
                               wsgiHeaders(environ),
                               environ['wsgi.input'],
                               WSGIWriter(start_response),
                               )
    except:
        import sys, traceback, _cputil
        exc_info = sys.exc_info()
        tb = traceback.format_exception(*exc_info)
        _cputil.getSpecialFunction('_cpLogMessage')("".join(tb))
        # TODO: override _cpdefaults._cpOnError() to call us back
        # in some way (maybe set a flag in the WSGIWriter), so that
        # we can still call start_response with an exc_info argument
        # even if doRequest traps its own errors.
        headers = [('Content-Type', 'text/plain'),
                   ('Content-Length', '0')]
        start_response("500 Internal Server Error", headers, exc_info)
    
    # We use the "write callable" hack, but we still must return an iterable.
    return []


def start():
    # Call the functions from cpg.server.onStartServerList
    for func in cpg.server.onStartServerList:
        func()

# "Start the server" on module import.
start()

def stop():
    # Call the functions from cpg.server.onStopThreadList
    for func in cpg.server.onStopThreadList:
        func()
    
    seen_threads.clear()
    
    # Call the functions from cpg.server.onStopServerList
    for func in cpg.server.onStopServerList:
        func()