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

import StringIO, Cookie
from cherrypy import cpg, _cphttptools, _cpserver

def init(*a, **kw):
    kw['initOnly'] = 1
    _cpserver.start(*a, **kw)

def wsgiApp(environ, start_response):
    cpg.request.method = environ['REQUEST_METHOD']
    # Rebuild first line of the request
    pathInfo = environ['PATH_INFO']
    qString = environ.get('QUERY_STRING')
    if qString:
        pathInfo += '?' + qString
    firstLine = '%s %s %s' % (
        environ['REQUEST_METHOD'],
        pathInfo,
        environ['SERVER_PROTOCOL']
    )
    _cphttptools.parseFirstLine(firstLine)

    # Initialize variables
    cpg.request.headerMap = {}
    cpg.request.simpleCookie = Cookie.SimpleCookie()
    cpg.response.simpleCookie = Cookie.SimpleCookie()

    # Rebuild headerMap
    for cgiName, headerName in [
        ('HTTP_HOST', 'Host'),
        ('HTTP_USER_AGENT', 'User-Agent'),
        ('HTTP_CGI_AUTHORIZATION', 'Authorization'),
        ('CONTENT_LENGTH', 'Content-Length'),
        ('CONTENT_TYPE', 'Content-Type'),
        ('HTTP_COOKIE', 'Cookie'),
        ('REMOTE_HOST', 'Remote-Host'),
        ('REMOTE_ADDR', 'Remote-Addr'),
        ('HTTP_REFERER', 'Referer'),
        ('HTTP_ACCEPT_ENCODING', 'Accept-Encoding'),
    ]:
        if cgiName in environ:
            _cphttptools.insertIntoHeaderMap(headerName, environ[cgiName])

    #  TODO: handle POST

    # Execute request
    wfile = StringIO.StringIO()
    _cphttptools.doRequest(wfile)
    response = wfile.getvalue()

    # Extract header from response
    headerLines = []
    i = 0
    while 1:
        j = response.find('\n', i)
        line = response[i:j]
        if line[-1] == '\r':
            line = line[:-1]
        headerLines.append(line)
        i = j+1
        if not line:
            break
    response = response[i:]

    status = headerLines[0]
    # Remove "HTTP/1.0" at the beginning of status
    i = status.find(' ')
    status = status[i+1:]

    responseHeaders = []
    for line in headerLines[1:]:
        i = line.find(':')
        header = line[:i]
        value = line[i+1:].lstrip()
        responseHeaders.append((header,value))

    start_response(status, responseHeaders)

    return response

