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
A high-speed, production ready, thread pooled, generic WSGI server.
"""

import socket
import thread
import Queue
import mimetools # todo: use email
import sys
import StringIO
import time
import traceback

class HTTPRequest(object):
    def __init__(self, socket, addr, server):
        self.socket = socket
        self.addr = addr
        self.server = server
        self.environ = None
        self.ready = False
        self.started_response = False
        self.status = None
        self.outheaders = None
        self.outheaderkeys = None
        self.buffer = StringIO.StringIO()
        self.rfile = self.socket.makefile("r", self.server.bufsize)
        self.wfile = self.socket.makefile("w", self.server.bufsize)
    def parse_request(self):
        self.environ = {}
        self.environ["wsgi.version"] = (1,0)
        self.environ["wsgi.url_scheme"] = "http"
        self.environ["wsgi.input"] = self.rfile
        self.environ["wsgi.errors"] = self.server.stderr
        self.environ["wsgi.multithread"] = True
        self.environ["wsgi.multiprocess"] = False
        self.environ["wsgi.run_once"] = False
        request_line = self.rfile.readline()
        method,path,version = request_line.strip().split(" ", 2)
        if "?" in path:
            path, qs = path.split("?", 1)
        else:
            qs = ""
        self.environ["REQUEST_METHOD"] = method
        self.environ["SCRIPT_NAME"] = path[1:]
        self.environ["PATH_INFO"] = ""
        self.environ["QUERY_STRING"] = qs
        self.environ["SERVER_PROTOCOL"] = version
        self.environ["SERVER_NAME"] = self.server.server_name
        self.environ["SERVER_PORT"] = str(self.server.bind_addr[1])
        # optional values
        self.environ["REMOTE_HOST"] = self.addr[0]
        self.environ["REMOTE_ADDR"] = self.addr[0]
        self.environ["REMOTE_PORT"] = str(self.addr[1])
        # then all the http headers
        headers = mimetools.Message(self.rfile)
        self.environ["CONTENT_TYPE"] = headers.getheader("Content-type", "")
        self.environ["CONTENT_LENGTH"] = headers.getheader("Content-length", "")
        for (k, v) in headers.items():
            envname = "HTTP_" + k.upper().replace("-","_")
            self.environ[envname] = v
        self.ready = True
    def start_response(self, status, headers, exc_info = None):
        # TODO: defaults
        if self.started_response:
            if not exc_info:
                assert False, "Already started response"
            else:
                try:
                    raise exc_info[0], exc_info[1], exc_info[2]
                finally:
                    exc_info = None
        self.started_response = True
        self.status = status
        self.outheaders = headers
        self.outheaderkeys = [key.lower() for (key,value) in self.outheaders]
        return self.buffer.write
    def do_output(self):
        if "content-length" not in self.outheaderkeys:
            self.outheaders.append(("Content-length", str(self.buffer.tell())))
        if "date" not in self.outheaderkeys:
            self.outheaders.append(("Date", time.ctime()))
        if "server" not in self.outheaderkeys:
            self.outheaders.append(("Server", self.server.version))
        self.wfile.write(self.environ["SERVER_PROTOCOL"] + " " + self.status + "\r\n")
        for (k,v) in self.outheaders:
            self.wfile.write(k + ": " + v + "\r\n")
        self.wfile.write("\r\n" + self.buffer.getvalue())
        self.wfile.flush()
    def terminate(self):
        self.rfile.close()
        self.wfile.close()
        self.socket.close()

def worker_thread(server):
    while True:
        try:
            request = server.requests.get()
            request.parse_request()
            # todo: handle exceptions in the next block
            response = server.wsgi_app(request.environ, request.start_response)
            for line in response: # write the response into the buffer
                request.buffer.write(line)
            request.do_output()
            request.terminate()
        except:
            self.server.handle_exception()

class CherryPyWSGIServer(object):
    version = "CherryPyWSGIServer/1.0" # none of this 0.1 uncertainty business
    def __init__(self, bind_addr, wsgi_app, numthreads=10, server_name=None, stderr=sys.stderr, bufsize=-1, max=-1):
        '''
        be careful w/ max
        '''
        self.requests = Queue.Queue(max)
        self.wsgi_app = wsgi_app
        self.bind_addr = bind_addr
        self.numthreads = numthreads
        if server_name:
            self.server_name = server_name
        else:
            self.server_name = socket.gethostname()
        self.stderr = stderr
        self.bufsize = bufsize
    def create_thread_pool(self):
        for i in xrange(0, self.numthreads):
            thread.start_new_thread(worker_thread, (self,))
    def start(self):
        '''
        run the server forever
        '''
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        self.socket.bind(self.bind_addr)
        self.socket.listen(5)
        self.create_thread_pool()
        while True:
            self.tick()
    def tick(self):
        s, addr = self.socket.accept()
        request = HTTPRequest(s, addr, self)
        self.requests.put(request)
        # optimized version follows
        #self.requests.put(HTTPRequest(*self.socket.accept()))
    def handle_exception(self):
        traceback.print_exc()
        
