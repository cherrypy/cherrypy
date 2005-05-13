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

import StringIO, Cookie, time
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
        pathInfo or '/',
        environ['SERVER_PROTOCOL']
    )
    _cphttptools.parseFirstLine(firstLine)

    # Initialize variables
    now = time.time()
    year, month, day, hh, mm, ss, wd, y, z = time.gmtime(now)
    date = "%s, %02d %3s %4d %02d:%02d:%02d GMT" % (_cphttptools.weekdayname[wd], day, _cphttptools.monthname[month], year, hh, mm, ss)
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

    # set up stuff similar to initRequest
    cpg.response.headerMap = {
        "protocolVersion": cpg.configOption.protocolVersion,
        "Status": "200 OK",
        "Content-Type": "text/html",
        "Server": "CherryPy/" + cpg.__version__,
        "Date": date,
        "Set-Cookie": [],
        "Content-Length": 0
    }
    cpg.request.base = "http://" + cpg.request.headerMap['Host']
    cpg.request.browserUrl = cpg.request.base + cpg.request.browserUrl
    cpg.request.isStatic = False
    cpg.request.parsePostData = True
    cpg.request.rfile = environ["wsgi.input"]
    cpg.request.objectPath = None 
    if 'Cookie' in cpg.request.headerMap:
        cpg.request.simpleCookie.load(cpg.request.headerMap['Cookie'])

    cpg.response.simpleCookie = Cookie.SimpleCookie()
    cpg.response.sendResponse = 1
    
    if cpg.request.method == 'POST' and cpg.request.parsePostData:
        _cphttptools.parsePostData(cpg.request.rfile)

    # Execute request
    wfile = StringIO.StringIO()
    cpg.response.wfile = wfile
    _cphttptools.handleRequest(wfile)
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

    return [response]

if __name__ == '__main__':
    from cherrypy import cpg, wsgiapp
    class Root:
        def index(self, name = "world"):
            count = cpg.request.sessionMap.get('count', 0) + 1
            cpg.request.sessionMap['count'] = count
            return """
                <html><body>
                Hello, %s, count is %s:
                <form action="/post" method="post">
                    Post some data: <input name=myData type=text"> <input type=submit>
                </form>
            """ % (name, count)
        index.exposed = True
        def post(self, myData):
            return "myData: " + myData
        post.exposed = True
    cpg.root = Root()
    
    import sys
    # This uses the WSGI HTTP server from PEAK.wsgiref
    # sys.path.append(r"C:\Tmp\PEAK\src")
    from wsgiref.simple_server import WSGIServer, WSGIRequestHandler
     # Read the CherryPy config file and initialize some variables
    wsgiapp.init(configMap = {'socketPort': 8000, 'sessionStorageType': 'ram'})
    server_address = ("", 8000)
    httpd = WSGIServer(server_address, WSGIRequestHandler)
    httpd.set_app(wsgiapp.wsgiApp)
    sa = httpd.socket.getsockname()
    print "Serving HTTP on", sa[0], "port", sa[1], "..."
    httpd.serve_forever()

