"""
Copyright (c) 2004, CherryPy Team (team@cherrypy.org)
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
    * Neither the name of the CherryPy Team nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import cpg, sys, threading, SocketServer, _cphttptools
import BaseHTTPServer, socket, Queue, _cputil

def stop():
    cpg._server.shutdown()

def start():
    """ Prepare the HTTP server and then run it """

    # If sessions are stored in files and we
    # use threading, we need a lock on the file
    if (cpg.configOption.threadPool > 1) and \
            cpg.configOption.sessionStorageType == 'file':
        cpg._sessionFileLock = threading.RLock()


    if cpg.configOption.socketFile:
        # AF_UNIX socket
        # TODO: Handle threading here
        class MyCherryHTTPServer(CherryHTTPServer): address_family = socket.AF_UNIX
    else:
        # AF_INET socket
        if cpg.configOption.threadPool > 1:
            MyCherryHTTPServer = PooledThreadServer
        else:
            MyCherryHTTPServer = CherryHTTPServer

    MyCherryHTTPServer.request_queue_size = cpg.configOption.socketQueueSize

    # Set protocol_version
    CherryHTTPRequestHandler.protocol_version = cpg.configOption.protocolVersion

    run_server(CherryHTTPRequestHandler, MyCherryHTTPServer, \
        (cpg.configOption.socketHost, cpg.configOption.socketPort), \
        cpg.configOption.socketFile)

def run_server(HandlerClass, ServerClass, server_address, socketFile):
    """Run the HTTP request handler class."""

    if cpg.configOption.socketFile:
        try: os.unlink(cpg.configOption.socketFile) # So we can reuse the socket
        except: pass
        server_address = cpg.configOption.socketFile
    if cpg.configOption.threadPool > 1:
        myCherryHTTPServer = ServerClass(server_address, cpg.configOption.threadPool, HandlerClass)
    else:
        myCherryHTTPServer = ServerClass(server_address, HandlerClass)
    cpg._server = myCherryHTTPServer
    if cpg.configOption.socketFile:
        try: os.chmod(socketFile, 0777) # So everyone can access the socket
        except: pass
    global _cpLogMessage
    _cpLogMessage = _cputil.getSpecialFunction('_cpLogMessage')

    servingWhat = "HTTP"
    if cpg.configOption.socketPort: onWhat = "socket: ('%s', %s)" % (cpg.configOption.socketHost, cpg.configOption.socketPort)
    else: onWhat = "socket file: %s" % cpg.configOption.socketFile
    _cpLogMessage("Serving %s on %s" % (servingWhat, onWhat), 'HTTP')

    try:
        # Call the functions from cpg.server.onStartServerList
        for func in cpg.server.onStartServerList:
            func()
        myCherryHTTPServer.serve_forever()
    except KeyboardInterrupt:
        _cpLogMessage("<Ctrl-C> hit: shutting down", "HTTP")
        myCherryHTTPServer.server_close()
    # Call the functions from cpg.server.onStartServerList
    for func in cpg.server.onStopServerList:
        func()

class CherryHTTPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):

    """CherryPy HTTP request handler with the following commands:

        o  GET
        o  HEAD
        o  POST
        o  HOTRELOAD

    """

    def address_string(self):
        """ Try to do a reverse DNS based on [server]reverseDNS in the config file """
        if cpg.configOption.reverseDNS:
            return BaseHTTPServer.BaseHTTPRequestHandler.address_string(self)
        else:
            return self.client_address[0]

    def do_GET(self):
        """Serve a GET request."""
        cpg.request.method = 'GET'
        _cphttptools.doRequest(
            self.client_address[0],
            self.address_string(),
            self.raw_requestline,
            self.headers,
            self.rfile,
            self.wfile
        )

    def do_HEAD(self): # Head is not implemented
        """Serve a HEAD request."""
        cpg.request.method = 'HEAD'
        _cphttptools.doRequest(
            self.client_address[0],
            self.address_string(),
            self.raw_requestline,
            self.headers,
            self.rfile,
            self.wfile
        )

    def do_POST(self):
        """Serve a POST request."""
        cpg.request.method = 'POST'
        _cphttptools.doRequest(
            self.client_address[0],
            self.address_string(),
            self.raw_requestline,
            self.headers,
            self.rfile,
            self.wfile
        )

        self.connection = self.request

    def log_message(self, format, *args):
        """ We have to override this to use our own logging mechanism """
        _cputil.getSpecialFunction('_cpLogMessage')(format % args, "HTTP")


class CherryHTTPServer(BaseHTTPServer.HTTPServer):
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
        except KeyboardInterrupt:
            _cpLogMessage("<Ctrl-C> hit: shutting down", "HTTP")
            self.shutdown()

    def serve_forever(self):
        """Override serve_forever to handle shutdown."""
        self.__running = 1
        while self.__running:
            self.handle_request()

    def shutdown(self):
        self.__running = 0

_SHUTDOWNREQUEST = (0,0)

class ServerThread(threading.Thread):
    def __init__(self, RequestHandlerClass, requestQueue, threadIndex):
        threading.Thread.__init__(self)
        self._RequestHandlerClass = RequestHandlerClass
        self._requestQueue = requestQueue
        self._threadIndex = threadIndex
        
    def run(self):
        # Call the functions from cpg.server.onStartThreadList
        for func in cpg.server.onStartThreadList:
            func()
        while 1:
            request, client_address = self._requestQueue.get()
            if (request, client_address) == _SHUTDOWNREQUEST:
                # Call the functions from cpg.server.onStopThreadList
                for func in cpg.server.onStopThreadList:
                    func()
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
        """ Handle an error gracefully.  May be overridden.
            The default is to print a traceback and continue.
        """
        import traceback, StringIO
        bodyFile=StringIO.StringIO()
        traceback.print_exc(file=bodyFile)
        errorBody=bodyFile.getvalue()
        bodyFile.close()
        _cputil.getSpecialFunction('_cpLogMessage')(errorBody)
        

class PooledThreadServer(SocketServer.TCPServer):

    allow_reuse_address = 1

    """A TCP Server using a pool of worker threads. This is superior to the
       alternatives provided by the Python standard library, which only offer
       (1) handling a single request at a time, (2) handling each request in
       a separate thread (via ThreadingMixIn), or (3) handling each request in
       a separate process (via ForkingMixIn). It's also superior in some ways
       to the pure async approach used by Twisted because it allows a more
       straightforward and simple programming model in the face of blocking
       requests (i.e. you don't have to bother with Deferreds).""" 
    def __init__(self, serverAddress, numThreads, RequestHandlerClass, ThreadClass=ServerThread):
        assert(numThreads > 0)
        # I know it says "do not override", but I have to in order to implement SSL support !
        SocketServer.BaseServer.__init__(self, serverAddress, RequestHandlerClass)
        self.socket=socket.socket(self.address_family, self.socket_type)
        self.server_bind()
        self.server_activate()

        self._numThreads = numThreads        
        self._RequestHandlerClass = RequestHandlerClass
        self._ThreadClass = ThreadClass
        self._requestQueue = Queue.Queue()
        self._workerThreads = []

    def createThread(self, threadIndex):
        return self._ThreadClass(self._RequestHandlerClass, self._requestQueue, threadIndex)
            
    def start(self):
        if self._workerThreads != []:
            return
        for i in xrange(self._numThreads):
            self._workerThreads.append(self.createThread(i))        
        for worker in self._workerThreads:
            worker.start()
            
    def server_close(self):
        """Override server_close to shutdown thread pool"""
        SocketServer.TCPServer.server_close(self)
        for worker in self._workerThreads:
            self._requestQueue.put(_SHUTDOWNREQUEST)
        for worker in self._workerThreads:
            worker.join()
        self._workerThreads = []

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

    def serve_forever(self):
        """Handle one request at a time until doomsday (or shutdown is called)."""
        if self._workerThreads == []:
            self.start()
        self.__running = 1
        while self.__running:
            if not self.handle_request():
                break
        self.server_close()            
        
    def handle_request(self):
        """Override handle_request to enqueue requests rather than handle
           them synchronously. Return 1 by default, 0 to shutdown the
           server."""
        try:
            request, client_address = self.get_request()
        except KeyboardInterrupt:
            _cpLogMessage("<Ctrl-C> hit: shutting down", "HTTP")
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

