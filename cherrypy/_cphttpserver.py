"""
Copyright (c) 2004, CherryPy Team (team@cherrypy.org)
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
    * Neither the name of the CherryPy Team nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import cpg, sys, threading, SocketServer, _cphttptools, BaseHTTPServer, socket, Cookie, Queue, _cputil

def start():
    """ Prepare the HTTP server and then run it """

    # TODO: SSL

    # If sessions are stored in files and we
    # use threading, we need a lock on the file
    if (cpg.configOption.threadPool > 1 or cpg.configOption.threading) and \
            cpg.configOption.sessionStorageType == 'file':
        cpg._sessionFileLock = threading.RLock()


    if cpg.configOption.socketFile:
        # AF_UNIX socket
        if cpg.configOption.forking:
            class MyCherryHTTPServer(SocketServer.ForkingMixIn,CherryHTTPServer): address_family = socket.AF_UNIX
        elif cpg.configOption.threading:
            class MyCherryHTTPServer(CherryThreadingMixIn,CherryHTTPServer): address_family = socket.AF_UNIX
        else:
            class MyCherryHTTPServer(CherryHTTPServer): address_family = socket.AF_UNIX
    else:
        # AF_INET socket
        if cpg.configOption.forking:
            class MyCherryHTTPServer(SocketServer.ForkingMixIn,CherryHTTPServer): pass
        elif cpg.configOption.threading:
            class MyCherryHTTPServer(CherryThreadingMixIn,CherryHTTPServer):pass
        elif cpg.configOption.threadPool > 1:
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
    if cpg.configOption.socketFile:
        try: os.chmod(socketFile, 0777) # So everyone can access the socket
        except: pass

    _cpLogMessage = _cputil.getSpecialFunction('_cpLogMessage')

    if cpg.configOption.sslKeyFile: servingWhat = "HTTPS"
    else: servingWhat = "HTTP"
    if cpg.configOption.socketPort: onWhat = "socket: ('%s', %s)" % (cpg.configOption.socketHost, cpg.configOption.socketPort)
    else: onWhat = "socket file: %s" % cpg.configOption.socketFile
    _cpLogMessage("Serving %s on %s" % (servingWhat, onWhat), 'HTTP')

    # If configOption.processPool is more than one, create new processes
    if cpg.configOption.processPool > 1:
        for i in range(cpg.configOption.processPool):
            _cpLogMessage("Forking a kid", "HTTP")
            if not os.fork():
                # Kid
                # initProcess(i)
                try: myCherryHTTPServer.serve_forever()
                except KeyboardInterrupt:
                    _cpLogMessage("<Ctrl-C> hit: shutting down", "HTTP")
                    myCherryHTTPServer.shutdownCtrlC()
    else:
        try: myCherryHTTPServer.serve_forever()
        except KeyboardInterrupt:
            _cpLogMessage("<Ctrl-C> hit: shutting down", "HTTP")
            myCherryHTTPServer.shutdownCtrlC()


class CherryHTTPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):

    """CherryPy HTTP request handler with the following commands:

        o  GET
        o  HEAD
        o  POST
        o  HOTRELOAD

    """

    def address_string(self):
        """ Try to do a reverse DNS based on [server]reverseDNS in the config file """
        if _reverseDNS: return BaseHTTPServer.BaseHTTPRequestHandler.address_string(self)
        else: return self.client_address[0]

    def cook_headers(self):
        """Process the headers in self.headers into the request.headerMap"""
        cpg.request.headerMap = {}
        cpg.request.simpleCookie = Cookie.SimpleCookie()
        cpg.response.simpleCookie = Cookie.SimpleCookie()

        # Build headerMap
        for item in self.headers.items():
            # Warning: if there is more than one header entry for cookies (AFAIK, only Konqueror does that)
            # only the last one will remain in headerMap (but they will be correctly stored in request.simpleCookie)
            _cphttptools.insertIntoHeaderMap(item[0],item[1])

        # Handle cookies differently because on Konqueror, multiple cookies come on different lines with the same key
        cookieList = self.headers.getallmatchingheaders('cookie')
        for cookie in cookieList:
            cpg.request.simpleCookie.load(cookie)

        if not cpg.request.headerMap.has_key('Remote-Addr'):
            try:
                cpg.request.headerMap['Remote-Addr'] = self.client_address[0]
                cpg.request.headerMap['Remote-Host'] = self.address_string()
            except: pass

        # Set peer_certificate (in SSL mode) so the web app can examinate the client certificate
        try: cpg.request.peerCertificate = self.request.get_peer_certificate()
        except: pass

        _cputil.getSpecialFunction('_cpLogMessage')("%s - %s" % (cpg.request.headerMap.get('Remote-Addr', ''), self.raw_requestline[:-2]), "HTTP")

    def do_GET(self):
        """Serve a GET request."""
        cpg.request.method = 'GET'
        _cphttptools.parseFirstLine(self.raw_requestline)
        self.cook_headers()
        _cphttptools.applyFilterList('afterRequestHeader')
        _cphttptools.applyFilterList('afterRequestBody')
        _cphttptools.doRequest(self.wfile)

    def do_HEAD(self): # Head is not implemented
        """Serve a HEAD request."""
        cpg.request.method = 'HEAD'
        _cphttptools.parseFirstLine(self.raw_requestline)
        self.cook_headers()
        _cphttptools.doRequest(self.wfile)

    def do_POST(self):
        """Serve a POST request."""
        cpg.request.method = 'POST'
        _cphttptools.parseFirstLine(self.raw_requestline)
        self.cook_headers()
        cpg.request.parsePostData = 1
        cpg.request.rfile = self.rfile
        _cphttptools.applyFilterList('afterRequestHeader')
        if cpg.request.parsePostData:
            _cphttptools.parsePostData(self.rfile)
        _cphttptools.applyFilterList('afterRequestBody')
        _cphttptools.doRequest(self.wfile)

    def setup(self):
        """ We have to override this to handle SSL
            (socket object from the OpenSSL package don't
            have the makefile method) """

        if not cpg.configOption.sslKeyFile:
            BaseHTTPServer.BaseHTTPRequestHandler.setup(self)

        """ SSL sockets from the OpenSSL package don't have the "makefile"
            method so we have to hack our way around this ... """

        class CherrySSLFileObject(socket._fileobject):
            """ This is used for implementing the "flush" methods
                for SSL sockets """

            def flush(self):
                """ Some sockets have a "sendall" method, some don't """
                if self._wbuf:
                    if hasattr(self._sock, "sendall"):
                        if type(self._wbuf)==type([]): # python2.3
                            self._sock.sendall("".join(self._wbuf))
                            self._wbuf=[]
                        else:
                            self._sock.sendall(self._wbuf)
                            self._wbuf=""
                    else:
                        while self._wbuf:
                            _sentChar=self._sock.send(self._wbuf)
                            self._wbuf=self._wbuf[_sentChar:]

        self.connection = self.request
        self.rfile = CherrySSLFileObject(self.connection, 'rb', self.rbufsize)
        self.wfile = CherrySSLFileObject(self.connection, 'wb', self.wbufsize)

    def log_message(self, format, *args):
        """ We have to override this to use our own logging mechanism """
        _cputil.getSpecialFunction('_cpLogMessage')(format % args, "HTTP")


class CherryHTTPServer(BaseHTTPServer.HTTPServer):
    def __init__(self, server_address, RequestHandlerClass):
        if not cpg.configOption.sslKeyFile:
            return BaseHTTPServer.HTTPServer.__init__(self, server_address, RequestHandlerClass)

        # I know it says "do not override", but I have to in order to implement SSL support !
        SocketServer.BaseServer.__init__(self, server_address, RequestHandlerClass)
        if cpg.sslKeyFile:
            self.socket = SSL.Connection(_sslCtx, socket.socket(self.address_family, self.socket_type))
        self.server_bind()
        self.server_activate()
        initAfterBind()

    def server_activate(self):
        """Override server_activate to set timeout on our listener socket"""
        if hasattr(self.socket, 'settimeout'): self.socket.settimeout(2)
        elif hasattr(self.socket, 'set_timeout'): self.socket.set_timeout(2)
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
        if hasattr(request,'setblocking'): # Jython doesn't have setblocking
            request.setblocking(1)
        return request, client_address

    def handle_request(self):
        """Override handle_request to trap timeout exception."""
        try:
            BaseHTTPServer.HTTPServer.handle_request(self)
        except socket.timeout: # TODO: Doesn't exist for older versions of python
            # The only reason for the timeout is so we can notice keyboard
            # interrupts on Win32, which don't interrupt accept() by default
            return 1
        except KeyboardInterrupt:
            print "<Ctrl-C> hit: shutting down"
            sys.exit(0)

    def shutdownCtrlC(self):
        self.shutdown()

_SHUTDOWNREQUEST = (0,0)

class ServerThread(threading.Thread):
    def __init__(self, RequestHandlerClass, requestQueue, threadIndex):
        threading.Thread.__init__(self)
        self._RequestHandlerClass = RequestHandlerClass
        self._requestQueue = requestQueue
        self._threadIndex = threadIndex
        self.setName("RUNNING")
        
    def run(self):
        _cputil.getSpecialFunction('_cpInitThread')(self._threadIndex)
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
        SocketServer.TCPServer.server_activate(self)

    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.server_address)

    def shutdown(self):
        """Gracefully shutdown a server that is serve_forever()ing."""
        self.__running = 0

    def shutdownCtrlC(self):
        self.server_close()

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
            if 1:
                for t in threading.enumerate():
                    if t.getName()=="NOT RUNNING": return 0
            request, client_address = self.get_request()
        except KeyboardInterrupt:
            print "<Ctrl-C> hit: shutting down"
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

