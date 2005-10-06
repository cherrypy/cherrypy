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
import threading
import Queue
import mimetools # todo: use email
import sys
import time
import traceback

weekdayname = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
monthname = [None, 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

class MaxSizeExceeded(Exception):
    pass

class SizeCheckWrapper(object):
    """ Wrapper around the rfile object. For each data reading method,
        it reads the data but it checks that the size of the data doesn't
        exceed a certain limit
    """
    def __init__(self, rfile, maxlen):
        self.rfile = rfile
        self.maxlen = maxlen
        self.bytes_read = 0
    def _check_length(self):
        if self.maxlen and self.bytes_read > self.maxlen:
            raise MaxSizeExceeded()
    def read(self, size = None):
        data = self.rfile.read(size)
        self.bytes_read += len(data)
        self._check_length()
        return data
    def readline(self, size = None):
        if size is not None:
            data = self.rfile.readline(size)
            self.bytes_read += len(data)
            self._check_length()
            return data

        # User didn't specify a size ...
        # We read the line in chunks to make sure it's not a 100MB line !
        res = []
        while True:
            data = self.rfile.readline(256)
            self.bytes_read += len(data)
            self._check_length()
            res.append(data)
            if len(data) < 256:
                return ''.join(res)
    def close(self):
        self.rfile.close()

    def __iter__(self):
        return self.rfile

    def next(self):
        data = self.rfile.next()
        self.bytes_read += len(data)
        self._check_length()
##      Normally the next method must raise StopIteration when it
##      fails but CP expects MaxSizeExceeded 
##        try:
##            self._check_length()
##        except:
##            raise StopIteration()
        return data

class HTTPRequest(object):
    def __init__(self, socket, addr, server):
        self.socket = socket
        self.addr = addr
        self.server = server
        self.environ = {}
        self.ready = False
        self.started_response = False
        self.status = ""
        self.outheaders = []
        self.outheaderkeys = []
        self.rfile = self.socket.makefile("r", self.server.bufsize)
        if self.server.config:
            mhs = self.server.config.get(
                'server.maxRequestHeaderSize',
                500 * 1024) # 500KB by default
            self.rfile = SizeCheckWrapper(self.rfile, mhs)
        self.wfile = self.socket.makefile("w", self.server.bufsize)
        self.sent_headers = False
    
    def parse_request(self):
        self.sent_headers = False
        self.environ = {}
        self.environ["wsgi.version"] = (1,0)
        self.environ["wsgi.url_scheme"] = "http"
        self.environ["wsgi.input"] = self.rfile
        self.environ["wsgi.errors"] = self.server.stderr
        self.environ["wsgi.multithread"] = True
        self.environ["wsgi.multiprocess"] = False
        self.environ["wsgi.run_once"] = False
        request_line = self.rfile.readline()
        if not request_line:
            self.ready = False
            return
        method,path,version = request_line.strip().split(" ", 2)
        if "?" in path:
            path, qs = path.split("?", 1)
        else:
            qs = ""
        self.environ["REQUEST_METHOD"] = method
        if path == "*":
            self.environ["SCRIPT_NAME"] = path
        else:
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

        # Request header is parsed
        # We prepare the SizeCheckWrapper for the request body
        if self.server.config:
            mbs = self.server.config.get(
                'server.maxRequestBodySize',
                100 * 1024 * 1024, # 100MB by default
                path = path)
            self.rfile.bytes_read = 0
            self.rfile.maxlen = mbs
    
    def start_response(self, status, headers, exc_info = None):
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
        return self.write
    
    def write(self, d):
        if not self.sent_headers:
            self.sent_headers = True
            self.send_headers()
        self.wfile.write(d)
        self.wfile.flush()
    
    def send_headers(self):
        if "content-length" not in self.outheaderkeys:
            self.close_at_end = True
        if "date" not in self.outheaderkeys:
            # HTTP 1.1 mandates date output in RFC 1123 format.
            year, month, day, hh, mm, ss, wd, y, z = time.gmtime()
            dt = ("%s, %02d %3s %4d %02d:%02d:%02d GMT" %
                  (weekdayname[wd], day, monthname[month], year, hh, mm, ss))
            self.outheaders.append(("Date", dt))
        if "server" not in self.outheaderkeys:
            self.outheaders.append(("Server", self.server.version))
        if (self.environ["SERVER_PROTOCOL"] == "HTTP/1.1"
            and "connection" not in self.outheaderkeys):
            self.outheaders.append(("Connection", "close"))
        self.wfile.write(self.environ["SERVER_PROTOCOL"] + " " + self.status + "\r\n")
        for (k,v) in self.outheaders:
            self.wfile.write(k + ": " + v + "\r\n")
        self.wfile.write("\r\n")
        self.wfile.flush()
    
    def terminate(self):
        if self.ready and not self.sent_headers and not self.server.interrupt:
            self.sent_headers = True
            self.send_headers()
        self.rfile.close()
        self.wfile.close()
        self.socket.close()


_SHUTDOWNREQUEST = None

class WorkerThread(threading.Thread):
    
    def __init__(self, server):
        self.ready = False
        self.server = server
        threading.Thread.__init__(self)
    
    def run(self):
        try:
            self.ready = True
            while True:
                request = self.server.requests.get()
                if request is _SHUTDOWNREQUEST:
                    return
                
                try:
                    try:
                        request.parse_request()
                        if request.ready:
                            response = self.server.wsgi_app(request.environ,
                                                            request.start_response)
                            for line in response:
                                request.write(line)
                    except socket.error, e:
                        errno = e.args[0]
                        if errno in (32, 104, 10053, 10054):
                            # Client probably closed the connection before the
                            # response was sent.
                            pass
                        else:
                            raise
                    except MaxSizeExceeded:
                        str = "Request Entity Too Large"
                        proto = request.environ.get("SERVER_PROTOCOL", "HTTP/1.0")
                        request.wfile.write("%s 413 %s\r\n" % (proto, str))
                        request.wfile.write("Content-Length: %s\r\n\r\n" % len(str))
                        request.wfile.write(str)
                        request.wfile.flush()
                    except (KeyboardInterrupt, SystemExit), exc:
                        self.server.interrupt = exc
                    except:
                        traceback.print_exc()
                finally:
                    request.terminate()
        except (KeyboardInterrupt, SystemExit), exc:
            self.server.interrupt = exc


class CherryPyWSGIServer(object):
    
    version = "CherryPy/2.1.0-rc2"
    ready = False
    interrupt = None
    
    def __init__(self, bind_addr, wsgi_app, numthreads=10, server_name=None,
                 stderr=sys.stderr, bufsize=-1, max=-1,
                 config = None):
        '''
        be careful w/ max
        '''
        self.requests = Queue.Queue(max)
        self.wsgi_app = wsgi_app
        self.bind_addr = bind_addr
        self.numthreads = numthreads or 1
        self.config = config
        if server_name:
            self.server_name = server_name
        else:
            self.server_name = socket.gethostname()
        self.stderr = stderr
        self.bufsize = bufsize
        self._workerThreads = []
    
    def start(self):
        '''
        run the server forever
        '''
        # We don't have to trap KeyboardInterrupt or SystemExit here,
        # because cherrpy.server already does so, calling self.stop() for us.
        # If you're using this server with another framework, you should
        # trap those exceptions in whatever code block calls start().
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.bind_addr)
        # Timeout so KeyboardInterrupt can be caught on Win32
        self.socket.settimeout(1)
        self.socket.listen(5)
        
        # Create worker threads
        for i in xrange(self.numthreads):
            self._workerThreads.append(WorkerThread(self))
        for worker in self._workerThreads:
            worker.start()
        for worker in self._workerThreads:
            while not worker.ready:
                time.sleep(.1)
        
        self.ready = True
        while self.ready:
            self.tick()
            if self.interrupt:
                raise self.interrupt
    
    def tick(self):
        try:
            s, addr = self.socket.accept()
            if hasattr(s, 'setblocking'):
                s.setblocking(1)
            request = HTTPRequest(s, addr, self)
            self.requests.put(request)
            # optimized version follows
            #self.requests.put(HTTPRequest(*self.socket.accept()))
        except socket.timeout:
            # The only reason for the timeout in start() is so we can
            # notice keyboard interrupts on Win32, which don't interrupt
            # accept() by default
            return
    
    def stop(self):
        """Gracefully shutdown a server that is serving forever."""
        self.ready = False
        self.socket.close()
        
        # Must shut down threads here so the code that calls
        # this method can know when all threads are stopped.
        for worker in self._workerThreads:
            self.requests.put(_SHUTDOWNREQUEST)
        
        # Don't join currentThread (when stop is called inside a request).
        current = threading.currentThread()
        for worker in self._workerThreads:
            if worker is not current and worker.isAlive:
                worker.join()
        
        self._workerThreads = []
