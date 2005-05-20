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

"""Simple tests for the wsgiapp module.

You'll have to run a browser and request http://localhost:8000/index and
/iterout to complete the test.
"""

from cherrypy import cpg


class Root(object):
    
    def index(self, name = "world"):
        count = cpg.request.sessionMap.get('count', 0) + 1
        cpg.request.sessionMap['count'] = count
        return """
            <html><body>
            Hello, %s, count is %s:
            <form action="/post" method="post">
                Post some data: <input name="myData" type=text" />
                <input type="submit" />
            </form>
            </body></html>""" % (name, count)
    index.exposed = True
    
    def post(self, myData):
        return "myData: " + myData
    post.exposed = True
    
    def iterout(self):
        # Set the Content-Length, larger than what we need (220 chars).
        # Do this outside the inner function. Otherwise, it would get
        # called too late (i.e., _after_ the Content-Length check in
        # _cphttptools.sendResponse, which would then force a collapse
        # of cpg.response.body before writing it out to the server).
        cpg.response.headerMap['Content-Length'] = 250
        def body():
            import time
            for i in xrange(5):
                # print to the console to help debug timing issues.
                print "iter %s" % i
                yield "Iteration #%s. Please wait 3 seconds...<br />" % i
                time.sleep(3)
            yield "5 iterations completed"
        return body()
    iterout.exposed = True

cpg.root = Root()

if __name__ == '__main__':
    # This uses the WSGI HTTP server from PEAK.wsgiref
    from wsgiref.simple_server import WSGIServer, WSGIRequestHandler
    from cherrypy import wsgiapp
    
    # Read the CherryPy config file and initialize some variables
    port = 8000
    wsgiapp.init(configMap = {'socketPort': port, 'sessionStorageType': 'ram'})
    httpd = WSGIServer(("", port), WSGIRequestHandler)
    httpd.set_app(wsgiapp.wsgiApp)
    sa = httpd.socket.getsockname()
    print "Serving HTTP on", sa[0], "port", sa[1], "..."
    httpd.serve_forever()
    