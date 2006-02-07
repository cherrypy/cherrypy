"""A native HTTP server for CherryPy."""

from BaseHTTPServer import BaseHTTPRequestHandler
import os
import Queue
import socket
import SocketServer
import sys
import threading
import time

import cherrypy
from cherrypy import _cputil
from cherrypy.lib import httptools


class CherryHTTPRequestHandler(BaseHTTPRequestHandler):
    """CherryPy HTTP request handler"""
    
    def address_string(self):
        """ Try to do a reverse DNS based on server.reverse_dns in the config file """
        if cherrypy.config.get('server.reverse_dns'):
            return BaseHTTPRequestHandler.address_string(self)
        else:
            return self.client_address[0]
    
    def _headerlist(self):
        hlist = []
        hit = 0
        for line in self.headers.headers:
            if line:
                if line[0] in ' \t':
                    # Continuation line. Add to previous entry.
                    if hlist:
                        hlist[-1][1] += " " + line.lstrip()
                else:
                    # New header. Add a new entry. We don't catch
                    # ValueError here because we trust rfc822.py.
                    name, value = line.split(":", 1)
                    hlist.append((name.strip(), value.strip()))
        return hlist
    
    def parse_request(self):
        # Extended to provide header and body length limits.
        mhs = int(cherrypy.config.get('server.max_request_header_size',
                                      500 * 1024))
        self.rfile = httptools.SizeCheckWrapper(self.rfile, mhs)
        try:
            presult = BaseHTTPRequestHandler.parse_request(self)
        except httptools.MaxSizeExceeded:
            self.send_error(413, "Request Entity Too Large")
            cherrypy.log(traceback=True)
            return False
        else:
            if presult:
                # Request header is parsed
                # We prepare the SizeCheckWrapper for the request body
                self.rfile.bytes_read = 0
                path = self.path
                if path == "*":
                    path = "global"
                mbs = int(cherrypy.config.get('server.max_request_body_size',
                                              100 * 1024 * 1024, path=path))
                self.rfile.maxlen = mbs
        return presult
    
    def handle_one_request(self):
        """Handle a single HTTP request."""
        
        self.raw_requestline = self.rfile.readline()
        if not self.raw_requestline:
            self.close_connection = 1
            return
        if not self.parse_request(): # An error code has been sent, just exit
            return
        
        request = None
        try:
            request = cherrypy.server.request(self.client_address,
                                              self.address_string(), "http")
            request.multithread = cherrypy.config.get("server.thread_pool") > 1
            request.multiprocess = False
            response = request.run(self.raw_requestline, self._headerlist(),
                                   self.rfile)
            s, h, b = response.status, response.header_list, response.body
            exc = None
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            tb = _cputil.formatExc()
            cherrypy.log(tb)
            if cherrypy.config.get("server.throw_errors", False):
                msg = "THROWN ERROR: %s" % sys.exc_info()[0].__name__
                s = "500 Internal Server Error"
                h = [('Content-Type', 'text/plain'),
                     ('Content-Length', str(len(msg)))]
                b = [msg]
            else:
                if not cherrypy.config.get("server.show_tracebacks", False):
                    tb = ""
                s, h, b = _cputil.bareError(tb)
        
        try:
            wfile = self.wfile
            wfile.write("%s %s\r\n" % (self.protocol_version, s))
            
            has_close_conn = False
            for name, value in h:
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
            for chunk in b:
                wfile.write(chunk)
            if request:
                request.close()
        except (KeyboardInterrupt, SystemExit), ex:
            try:
                if request:
                    request.close()
            except:
                cherrypy.log(traceback=True)
            raise ex
        except:
            cherrypy.log(traceback=True)
            try:
                if request:
                    request.close()
            except:
                cherrypy.log(traceback=True)
            
            s, h, b = _cputil.bareError()
            # CherryPy test suite expects bareError body to be output,
            # so don't call start_response (which, according to PEP 333,
            # may raise its own error at that point).
            for chunk in b:
                wfile.write(chunk)
        
        if self.command == "POST":
            self.connection = self.request
        
        # Close the conn, since we do not yet support persistent connections.
        self.close_connection = 1
    
    def log_message(self, format, *args):
        """ We have to override this to use our own logging mechanism """
        cherrypy.log(format % args, "HTTP")


class CherryHTTPServer(SocketServer.BaseServer):
    # Subclass BaseServer (instead of BaseHTTPServer.HTTPServer), because
    # getfqdn call was timing out on localhost when calling gethostbyaddr.
    
    ready = False
    interrupt = None
    RequestHandlerClass = CherryHTTPRequestHandler
    allow_reuse_address = True
    
    def __init__(self):
        # SocketServer __init__'s all say "do not override",
        # but we have to in order to implement SSL and IPv6 support!
        
        # Set protocol_version
        httpproto = cherrypy.config.get('server.protocol_version') or "HTTP/1.0"
        self.RequestHandlerClass.protocol_version = httpproto
        
        self.request_queue_size = cherrypy.config.get('server.socket_queue_size')
        
        # Select the appropriate server based on config options
        sockFile = cherrypy.config.get('server.socket_file')
        if sockFile:
            # AF_UNIX socket
            self.address_family = socket.AF_UNIX
            
            # So we can reuse the socket
            try: os.unlink(sockFile)
            except: pass
            
            # So everyone can access the socket
            try: os.chmod(sockFile, 0777)
            except: pass
            
            self.server_address = sockFile
            self.socket = socket.socket(self.address_family, self.socket_type)
            self.server_bind()
        else:
            # AF_INET or AF_INET6 socket
            host = cherrypy.config.get('server.socket_host')
            port = cherrypy.config.get('server.socket_port')
            self.server_address = (host, port)
            
            try:
                info = socket.getaddrinfo(host, port, socket.AF_UNSPEC,
                                          socket.SOCK_STREAM)
            except socket.gaierror:
                # Probably a DNS issue.
                # Must...refuse...temptation..to..guess...
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.socket.bind(self.server_address)
            else:
                # Get the correct address family for our host (allows IPv6 addresses)
                for res in info:
                    af, socktype, proto, canonname, sa = res
                    self.address_family = af
                    self.socket_type = socktype
                    try:
                        self.socket = socket.socket(af, socktype, proto)
                        self.server_bind()
                    except socket.error, msg:
                        if self.socket:
                            self.socket.close()
                        self.socket = None
                        continue
                    break
                if not self.socket:
                    raise socket.error, msg
        
        self.server_activate()
    
    def server_activate(self):
        """Override server_activate to set timeout on our listener socket"""
        self.socket.settimeout(1)
        self.socket.listen(self.request_queue_size)
    
    def server_bind(self):
        """Called by constructor to bind the socket."""
        if self.allow_reuse_address:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.server_address)
    
    def close_request(self, request):
        """Called to clean up an individual request."""
        request.close()
    
    def get_request(self):
        # With Python 2.3 it seems that an accept socket in timeout
        # (nonblocking) mode results in request sockets that are also set
        # in nonblocking mode. Since that doesn't play well with makefile()
        # (where wfile and rfile are set in SocketServer.py) we explicitly
        # set the request socket to blocking
        request, client_address = self.socket.accept()
        if hasattr(request, 'setblocking'):
            request.setblocking(1)
        return request, client_address
    
    def handle_request(self):
        """Handle one request, possibly blocking."""
        # Overridden to trap socket.timeout and KeyboardInterrupt/SystemExit.
        try:
            request, client_address = self.get_request()
        except (socket.error, socket.timeout):
            # The only reason for the timeout is so we can notice keyboard
            # interrupts on Win32, which don't interrupt accept() by default
            return
        
        try:
            self.process_request(request, client_address)
        except (KeyboardInterrupt, SystemExit):
            self.close_request(request)
            raise
        except:
            self.handle_error(request, client_address)
            self.close_request(request)
    
    def handle_error(self, request, client_address):
        cherrypy.log(traceback=True)
    
    def serve_forever(self):
        """Override serve_forever to handle shutdown."""
        self.ready = True
        while self.ready:
            if self.interrupt:
                raise self.interrupt
            self.handle_request()
        self.server_close()
    start = serve_forever
    
    def server_close(self):
        self.ready = False
        self.socket.close()
    stop = shutdown = server_close


class PooledThreadServer(CherryHTTPServer):
    """A TCP Server using a pool of worker threads. This is superior to the
       alternatives provided by the Python standard library, which only offer
       (1) handling a single request at a time, (2) handling each request in
       a separate thread (via ThreadingMixIn), or (3) handling each request in
       a separate process (via ForkingMixIn). It's also superior in some ways
       to the pure async approach used by Twisted because it allows a more
       straightforward and simple programming model in the face of blocking
       requests (i.e. you don't have to bother with Deferreds)."""
    
    def __init__(self):
        self.numThreads = cherrypy.config.get('server.thread_pool')
        self.ThreadClass = ServerThread
        self.requestQueue = Queue.Queue()
        self.workerThreads = []
        CherryHTTPServer.__init__(self)
    
    def process_request(self, request, client_address):
        """Call finish_request."""
        self.finish_request(request, client_address)
        # Let the ServerThread close the request when it's finished.
##      NO!  self.close_request(request)
    
    def finish_request(self, request, client_address):
        """Finish one request by passing it to the Queue."""
        self.requestQueue.put((request, client_address))
    
    def createThread(self):
        return self.ThreadClass(self.RequestHandlerClass, self.requestQueue, self)
    
    def serve_forever(self):
        """Handle one request at a time until doomsday (or shutdown is called)."""
        if self.workerThreads == []:
            for i in xrange(self.numThreads):
                self.workerThreads.append(self.createThread())
            for worker in self.workerThreads:
                worker.start()
        
        for worker in self.workerThreads:
            while not worker.ready:
                time.sleep(.1)
        
        CherryHTTPServer.serve_forever(self)
    start = serve_forever
    
    def server_close(self):
        """Gracefully shutdown a server that is serve_forever()ing."""
        CherryHTTPServer.server_close(self)
        
        # Must shut down threads here so the code that calls
        # this method can know when all threads are stopped.
        for worker in self.workerThreads:
            self.requestQueue.put(_SHUTDOWNREQUEST)
        current = threading.currentThread()
        for worker in self.workerThreads:
            if worker is not current and worker.isAlive:
                worker.join()
        self.workerThreads = []
    stop = shutdown = server_close


_SHUTDOWNREQUEST = (0,0)

class ServerThread(threading.Thread):
    
    def __init__(self, RequestHandlerClass, requestQueue, server):
        self.server = server
        self.ready = False
        threading.Thread.__init__(self)
        self.RequestHandlerClass = RequestHandlerClass
        self.requestQueue = requestQueue
    
    def run(self):
        try:
            self.ready = True
            while 1:
                request, client_address = self.requestQueue.get()
                if (request, client_address) == _SHUTDOWNREQUEST:
                    return
                try:
                    try:
                        self.RequestHandlerClass(request, client_address, self)
                    except (KeyboardInterrupt, SystemExit):
                        raise
                    except:
                        cherrypy.log(traceback=True)
                finally:
                    request.close()
        except (KeyboardInterrupt, SystemExit), exc:
            self.server.interrupt = exc


def embedded_server(handler=None):
    """Selects and instantiates the appropriate server."""
    
    # Select the appropriate server based on config options
    if cherrypy.config.get('server.thread_pool', 1) > 1:
        ServerClass = PooledThreadServer
    else:
        ServerClass = CherryHTTPServer
    return ServerClass()

