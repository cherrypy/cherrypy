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

import threading, os, socket
import SocketServer, BaseHTTPServer, Queue
import cherrypy
from cherrypy import _cputil, _cphttptools

try:
    import cStringIO as StringIO
except ImportError:
    import StringIO


class CherryHTTPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    
    """CherryPy HTTP request handler with the following commands:
        
        o  GET
        o  HEAD
        o  POST
        o  HOTRELOAD
        
    """
    
    def address_string(self):
        """ Try to do a reverse DNS based on [server]reverseDNS in the config file """
        if cherrypy.config.get('server.reverseDNS'):
            return BaseHTTPServer.BaseHTTPRequestHandler.address_string(self)
        else:
            return self.client_address[0]
    
    def _headerlist(self):
        list = []
        hit = 0
        for line in self.headers.headers:
            if line:
                if line[0] in ' \t':
                    # Continuation line. Add to previous entry.
                    if list:
                        list[-1][1] += " " + line.lstrip()
                else:
                    # New header. Add a new entry. We don't catch
                    # ValueError here because we trust rfc822.py.
                    name, value = line.split(":", 1)
                    list.append((name.strip(), value.strip()))
        return list
    
    def handle_one_request(self):
        """Handle a single HTTP request."""
        
        self.raw_requestline = self.rfile.readline()
        if not self.raw_requestline:
            self.close_connection = 1
            return
        if not self.parse_request(): # An error code has been sent, just exit
            return
        
        cherrypy.request.multithread = cherrypy.config.get("server.threadPool") > 1
        cherrypy.request.multiprocess = False
        cherrypy.server.request(self.client_address[0],
                                self.address_string(),
                                self.raw_requestline,
                                self._headerlist(),
                                self.rfile, "http")
        wfile = self.wfile
        wfile.write("%s %s\r\n" % (self.protocol_version, cherrypy.response.status))
        
        has_close_conn = False
        for name, value in cherrypy.response.headers:
            wfile.write("%s: %s\r\n" % (name, value))
            if name.lower == 'connection' and value.lower == 'close':
                has_close_conn = True
        if not has_close_conn:
            # This server doesn't support persistent connections yet, so we
            # must add a "Connection: close" header to tell the client that
            # we will close the connection when we're done sending output.
            # 
            # From RFC 2616 sec 14.10:
            # HTTP/1.1 defines the "close" connection option for the sender
            # to signal that the connection will be closed after completion
            # of the response. For example,
            # 
            #    Connection: close
            # 
            # in either the request or the response header fields indicates
            # that the connection SHOULD NOT be considered `persistent'
            # (section 8.1) after the current request/response is complete.
            # 
            # HTTP/1.1 applications that do not support persistent connections
            # MUST include the "close" connection option in every message.
            wfile.write("Connection: close\r\n")
        
        wfile.write("\r\n")
        try:
            for chunk in cherrypy.response.body:
                wfile.write(chunk)
        except:
            s, h, b = _cphttptools.bareError()
            for chunk in b:
                wfile.write(chunk)
        
        if self.command == "POST":
            self.connection = self.request
        
        # Close the conn, since we do not yet support persistent connections.
        self.close_connection = 1
    
    def log_message(self, format, *args):
        """ We have to override this to use our own logging mechanism """
        cherrypy.log(format % args, "HTTP")


class CherryHTTPServer(BaseHTTPServer.HTTPServer):
    
    def __init__(self):
        # Set protocol_version
        proto = cherrypy.config.get('server.protocolVersion') or "HTTP/1.0"
        CherryHTTPRequestHandler.protocol_version = proto
        
        # Select the appropriate server based on config options
        sockFile = cherrypy.config.get('server.socketFile')
        if sockFile:
            # AF_UNIX socket
            self.address_family = socket.AF_UNIX
            
            # So we can reuse the socket
            try: os.unlink(sockFile)
            except: pass
            
            # So everyone can access the socket
            try: os.chmod(sockFile, 0777)
            except: pass
            
            server_address = sockFile
        else:
            # AF_INET socket
            server_address = (cherrypy.config.get('server.socketHost'),
                              cherrypy.config.get('server.socketPort'))
        
        self.request_queue_size = cherrypy.config.get('server.socketQueueSize')
        
        BaseHTTPServer.HTTPServer.__init__(self, server_address, CherryHTTPRequestHandler)
    
    def server_activate(self):
        """Override server_activate to set timeout on our listener socket"""
        self.socket.settimeout(1)
        BaseHTTPServer.HTTPServer.server_activate(self)
    
    def server_bind(self):
        # Removed getfqdn call because it was timing out on localhost when calling gethostbyaddr
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.server_address)
    
    def get_request(self):
        # With Python 2.3 it seems that an accept socket in timeout (nonblocking) mode
        #  results in request sockets that are also set in nonblocking mode. Since that doesn't play
        #  well with makefile() (where wfile and rfile are set in SocketServer.py) we explicitly set
        #  the request socket to blocking
        
        request, client_address = self.socket.accept()
        request.setblocking(1)
        return request, client_address
    
    def handle_request(self):
        """Override handle_request to trap timeout exception."""
        try:
            BaseHTTPServer.HTTPServer.handle_request(self)
        except socket.timeout:
            # The only reason for the timeout is so we can notice keyboard
            # interrupts on Win32, which don't interrupt accept() by default
            return 1
        except (KeyboardInterrupt, SystemExit):
            cherrypy.log("<Ctrl-C> hit: shutting down http server", "HTTP")
            self.shutdown()
    
    def serve_forever(self):
        """Override serve_forever to handle shutdown."""
        self.__running = 1
        while self.__running:
            self.handle_request()
    start = serve_forever
    
    def shutdown(self):
        self.__running = 0
    stop = shutdown


_SHUTDOWNREQUEST = (0,0)

class ServerThread(threading.Thread):
    
    def __init__(self, RequestHandlerClass, requestQueue):
        threading.Thread.__init__(self)
        self._RequestHandlerClass = RequestHandlerClass
        self._requestQueue = requestQueue
    
    def run(self):
        while 1:
            request, client_address = self._requestQueue.get()
            if (request, client_address) == _SHUTDOWNREQUEST:
                return
            if self.verify_request(request, client_address):
                try:
                    self.process_request(request, client_address)
                except:
                    self.handle_error(request, client_address)
                    self.close_request(request)
            else:
                self.close_request(request)
    
    def verify_request(self, request, client_address):
        """ Verify the request.  May be overridden.
            Return 1 if we should proceed with this request. """
        return 1
    
    def process_request(self, request, client_address):
        self._RequestHandlerClass(request, client_address, self)
        self.close_request(request)
    
    def close_request(self, request):
        """ Called to clean up an individual request. """
        request.close()
    
    def handle_error(self, request, client_address):
        """Handle an error gracefully.  May be overridden."""
        errorBody = _cputil.formatExc()
        cherrypy.log(errorBody)


class PooledThreadServer(SocketServer.TCPServer):
    """A TCP Server using a pool of worker threads. This is superior to the
       alternatives provided by the Python standard library, which only offer
       (1) handling a single request at a time, (2) handling each request in
       a separate thread (via ThreadingMixIn), or (3) handling each request in
       a separate process (via ForkingMixIn). It's also superior in some ways
       to the pure async approach used by Twisted because it allows a more
       straightforward and simple programming model in the face of blocking
       requests (i.e. you don't have to bother with Deferreds)."""
    
    allow_reuse_address = 1
    
    def __init__(self):
        # Set protocol_version
        proto = cherrypy.config.get('server.protocolVersion') or "HTTP/1.0"
        CherryHTTPRequestHandler.protocol_version = proto
        
        # Select the appropriate server based on config options
        threadPool = cherrypy.config.get('server.threadPool')
        server_address = (cherrypy.config.get('server.socketHost'),
                          cherrypy.config.get('server.socketPort'))
        self.request_queue_size = cherrypy.config.get('server.socketQueueSize')
        
        # I know it says "do not override", but I have to in order to implement SSL support !
        SocketServer.BaseServer.__init__(self, server_address, CherryHTTPRequestHandler)
        self.socket = socket.socket(self.address_family, self.socket_type)
        self.server_bind()
        self.server_activate()
        
        self._numThreads = threadPool
        self._RequestHandlerClass = CherryHTTPRequestHandler
        self._ThreadClass = ServerThread
        self._requestQueue = Queue.Queue()
        self._workerThreads = []
    
    def createThread(self):
        return self._ThreadClass(self._RequestHandlerClass, self._requestQueue)
    
    def server_activate(self):
        """Override server_activate to set timeout on our listener socket"""
        self.socket.settimeout(1)
        SocketServer.TCPServer.server_activate(self)
    
    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.server_address)
    
    def shutdown(self):
        """Gracefully shutdown a server that is serve_forever()ing."""
        self.__running = 0
        
        # Must shut down threads here so the code that calls
        # this method can know when all threads are stopped.
        for worker in self._workerThreads:
            self._requestQueue.put(_SHUTDOWNREQUEST)
        current = threading.currentThread()
        for worker in self._workerThreads:
            if worker is not current:
                worker.join()
        self._workerThreads = []
    stop = shutdown
    
    def serve_forever(self):
        """Handle one request at a time until doomsday (or shutdown is called)."""
        if self._workerThreads == []:
            for i in xrange(self._numThreads):
                self._workerThreads.append(self.createThread())
            for worker in self._workerThreads:
                worker.start()
        self.__running = 1
        while self.__running:
            if not self.handle_request():
                break
        self.server_close()
    start = serve_forever
    
    def handle_request(self):
        """Override handle_request to enqueue requests rather than handle
           them synchronously. Return 1 by default, 0 to shutdown the
           server."""
        try:
            request, client_address = self.get_request()
        except (KeyboardInterrupt, SystemExit):
            cherrypy.log("<Ctrl-C> hit: shutting down", "HTTP")
            return 0
        except socket.error, e:
            return 1
        self._requestQueue.put((request, client_address))
        return 1
    
    def get_request(self):
        # With Python 2.3 it seems that an accept socket in timeout (nonblocking) mode
        #  results in request sockets that are also set in nonblocking mode. Since that doesn't play
        #  well with makefile() (where wfile and rfile are set in SocketServer.py) we explicitly set
        #  the request socket to blocking

        request, client_address = self.socket.accept()
        if hasattr(request,'setblocking'):
            request.setblocking(1)
        return request, client_address


def embedded_server(handler=None):
    """Selects and instantiates the appropriate server."""
    
    # Select the appropriate server based on config options
    sockFile = cherrypy.config.get('server.socketFile')
    threadPool = cherrypy.config.get('server.threadPool')
    if threadPool > 1 and not sockFile:
        ServerClass = PooledThreadServer
    else:
        ServerClass = CherryHTTPServer
    return ServerClass()

