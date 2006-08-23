"""A high-speed, production ready, thread pooled, generic WSGI server."""

import mimetools # todo: use email
import Queue
import re
quoted_slash = re.compile("(?i)%2F")
import rfc822
import socket
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO
import sys
import threading
import time
import traceback
from urllib import unquote
from urlparse import urlparse

import errno
socket_errors_to_ignore = []
# Not all of these names will be defined for every platform.
for _ in ("EPIPE", "ETIMEDOUT", "ECONNREFUSED", "ECONNRESET",
          "EHOSTDOWN", "EHOSTUNREACH",
          "WSAECONNABORTED", "WSAECONNREFUSED", "WSAECONNRESET",
          "WSAENETRESET", "WSAETIMEDOUT"):
    if _ in dir(errno):
        socket_errors_to_ignore.append(getattr(errno, _))
# de-dupe the list
socket_errors_to_ignore = dict.fromkeys(socket_errors_to_ignore).keys()

# These are lowercase because mimetools.Message uses lowercase keys.
comma_separated_headers = [
    'accept', 'accept-charset', 'accept-encoding', 'accept-language',
    'accept-ranges', 'allow', 'cache-control', 'connection', 'content-encoding',
    'content-language', 'expect', 'if-match', 'if-none-match', 'pragma',
    'proxy-authenticate', 'te', 'trailer', 'transfer-encoding', 'upgrade',
    'vary', 'via', 'warning', 'www-authenticate',
    ]


class HTTPRequest(object):
    
    def __init__(self, connection):
        self.connection = connection
        self.rfile = self.connection.rfile
        self.environ = connection.environ.copy()
        
        self.ready = False
        self.started_response = False
        self.status = ""
        self.outheaders = []
        self.sent_headers = False
        self.close_connection = False
    
    def parse_request(self):
        request_line = None
        try:
            request_line = self.rfile.readline()
        except socket.timeout:
            self.simple_response("408 Request Timeout")
            return
        
        if not request_line:
            return
        
        server = self.connection.server
        
        method, path, req_protocol = request_line.strip().split(" ", 2)
        self.environ["REQUEST_METHOD"] = method
        
        # path may be an abs_path (including "http://host.domain.tld");
        scheme, location, path, params, qs, frag = urlparse(path)
        if scheme:
            self.environ["wsgi.url_scheme"] = scheme
        if params:
            path = path + ";" + params
        
        # Unquote the path+params (e.g. "/this%20path" -> "this path").
        # http://www.w3.org/Protocols/rfc2616/rfc2616-sec5.html#sec5.1.2
        #
        # But note that "...a URI must be separated into its components
        # before the escaped characters within those components can be
        # safely decoded." http://www.ietf.org/rfc/rfc2396.txt, sec 2.4.2
        atoms = [unquote(x) for x in quoted_slash.split(path)]
        path = "%2F".join(atoms)
        
        for mount_point, wsgi_app in server.mount_points:
            if path == "*":
                # This means, of course, that the first wsgi_app will
                # always handle a URI of "*".
                self.environ["SCRIPT_NAME"] = ""
                self.environ["PATH_INFO"] = "*"
                self.wsgi_app = wsgi_app
                break
            # The mount_points list should be sorted by length, descending.
            if path.startswith(mount_point):
                self.environ["SCRIPT_NAME"] = mount_point
                self.environ["PATH_INFO"] = path[len(mount_point):]
                self.wsgi_app = wsgi_app
                break
        else:
            self.simple_response("404 Not Found")
            return
        
        # Note that, like wsgiref and most other WSGI servers,
        # we unquote the path but not the query string.
        self.environ["QUERY_STRING"] = qs
        
        # Compare request and server HTTP protocol versions, in case our
        # server does not support the requested protocol. Limit our output
        # to min(req, server). We want the following output:
        #     request    server     actual written   supported response
        #     protocol   protocol  response protocol    feature set
        # a     1.0        1.0           1.0                1.0
        # b     1.0        1.1           1.1                1.0
        # c     1.1        1.0           1.0                1.0
        # d     1.1        1.1           1.1                1.1
        # Notice that, in (b), the response will be "HTTP/1.1" even though
        # the client only understands 1.0. RFC 2616 10.5.6 says we should
        # only return 505 if the _major_ version is different.
        rp = int(req_protocol[5]), int(req_protocol[7])
        sp = int(server.protocol[5]), int(server.protocol[7])
        if sp[0] != rp[0]:
            self.simple_response("505 HTTP Version Not Supported")
            return
        # Bah. "SERVER_PROTOCOL" is actually the REQUEST protocol.
        self.environ["SERVER_PROTOCOL"] = req_protocol
        # set a non-standard environ entry so the WSGI app can know what
        # the *real* server protocol is (and what features to support).
        self.environ["ACTUAL_SERVER_PROTOCOL"] = server.protocol
        self.response_protocol = "HTTP/%s.%s" % min(rp, sp)
        
        # If the Request-URI was an absoluteURI, use its location atom.
        if location:
            self.environ["SERVER_NAME"] = location
        
        # then all the http headers
        headers = mimetools.Message(self.rfile)
        self.environ.update(self.parse_headers(headers))
        
        # Persistent connection support
        if self.response_protocol == "HTTP/1.1":
            if headers.getheader("Connection", "") == "close":
                self.close_connection = True
                self.outheaders.append(("Connection", "close"))
        else:
            if headers.getheader("Connection", "") == "Keep-Alive":
                if self.close_connection == False:
                    self.outheaders.append(("Connection", "Keep-Alive"))
            else:
                self.close_connection = True
        
        # Transfer-Encoding support
        te = headers.getheader("Transfer-Encoding", "")
        te = [x.strip() for x in te.split(",") if x.strip()]
        if te:
            while te:
                enc = te.pop()
                if enc.lower() == "chunked":
                    if not self.decode_chunked():
                        return
                else:
                    self.simple_response("501 Unimplemented")
                    self.close_connection = True
                    return
        else:
            cl = headers.getheader("Content-length")
            if method in ("POST", "PUT") and cl is None:
                # No Content-Length header supplied. This will hang
                # cgi.FieldStorage, since it cannot determine when to
                # stop reading from the socket. Until we handle chunked
                # encoding, always respond with 411 Length Required.
                # See http://www.cherrypy.org/ticket/493.
                self.simple_response("411 Length Required")
                return
        
        # From PEP 333:
        # "Servers and gateways that implement HTTP 1.1 must provide
        # transparent support for HTTP 1.1's "expect/continue" mechanism.
        # This may be done in any of several ways:
        #   1. Respond to requests containing an Expect: 100-continue request
        #      with an immediate "100 Continue" response, and proceed normally.
        #   2. Proceed with the request normally, but provide the application
        #      with a wsgi.input stream that will send the "100 Continue"
        #      response if/when the application first attempts to read from
        #      the input stream. The read request must then remain blocked
        #      until the client responds.
        #   3. Wait until the client decides that the server does not support
        #      expect/continue, and sends the request body on its own.
        #      (This is suboptimal, and is not recommended.)
        #
        # We used to do 3, but are now doing 1. Maybe we'll do 2 someday,
        # but it seems like it would be a big slowdown for such a rare case.
        if headers.getheader("Expect", "") == "100-continue":
            self.simple_response(100)
        
        self.ready = True
    
    def parse_headers(self, headers):
        environ = {}
        environ["CONTENT_TYPE"] = headers.getheader("Content-type", "")
        environ["CONTENT_LENGTH"] = headers.getheader("Content-length") or ""
        
        for k in headers:
            envname = "HTTP_" + k.upper().replace("-", "_")
            if k in comma_separated_headers:
                environ[envname] = ", ".join(headers.getheaders(k))
            elif k in ('Transfer-Encoding',):
                pass
            else:
                environ[envname] = headers[k]
        return environ
    
    def decode_chunked(self):
        """Decode the 'chunked' transfer coding."""
        cl = 0
        data = StringIO.StringIO()
        while True:
            line = self.rfile.readline().strip().split(" ", 1)
            chunk_size = int(line.pop(0), 16)
            if chunk_size <= 0:
                break
##            if line: chunk_extension = line[0]
            cl += chunk_size
            data.write(self.rfile.read(chunk_size))
            crlf = self.rfile.read(2)
            if crlf != "\r\n":
                self.simple_response("400 Bad Request",
                                     "Bad chunked transfer coding "
                                     "(expected '\\r\\n', got %r)" % crlf)
                return
        
        headers = mimetools.Message(self.rfile)
        self.environ.update(self.parse_headers(headers))
        data.seek(0)
        self.environ["wsgi.input"] = data
        self.environ["CONTENT_LENGTH"] = str(cl) or ""
        return True
    
    def respond(self):
        response = self.wsgi_app(self.environ, self.start_response)
        for line in response:
            self.write(line)
        if hasattr(response, "close"):
            response.close()
        self.terminate()
    
    def simple_response(self, status, msg=""):
        """Write a simple response back to the client."""
        status = str(status)
        wfile = self.connection.wfile
        wfile.write("%s %s\r\n" % (self.connection.server.protocol, status))
        wfile.write("Content-Length: %s\r\n" % len(msg))
        
        if status[:3] == "413" and self.response_protocol == 'HTTP/1.1':
            # Request Entity Too Large
            self.close_connection = True
            wfile.write("Connection: close\r\n")
        
        wfile.write("\r\n")
        if msg:
            wfile.write(msg)
        wfile.flush()
    
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
        self.outheaders.extend(headers)
        return self.write
    
    def write(self, d):
        if not self.sent_headers:
            self.sent_headers = True
            self.send_headers()
        self.connection.wfile.write(d)
        self.connection.wfile.flush()
    
    def send_headers(self):
        hkeys = [key.lower() for (key,value) in self.outheaders]
        
        if (self.response_protocol == 'HTTP/1.1'
            and (# Request Entity Too Large. Close conn to avoid garbage.
                self.status[:3] == "413"
                # No Content-Length. Close conn to determine transfer-length.
                or "content-length" not in hkeys)):
            if "connection" not in hkeys:
                self.outheaders.append(("Connection", "close"))
            self.close_connection = True
        
        if "date" not in hkeys:
            self.outheaders.append(("Date", rfc822.formatdate()))
        
        server = self.connection.server
        wfile = self.connection.wfile
        
        if "server" not in hkeys:
            self.outheaders.append(("Server", server.version))
        
        wfile.write(server.protocol + " " + self.status + "\r\n")
        for k, v in self.outheaders:
            wfile.write(k + ": " + v + "\r\n")
        wfile.write("\r\n")
        wfile.flush()
    
    def terminate(self):
        if (self.ready and not self.sent_headers
                and not self.connection.server.interrupt):
            self.sent_headers = True
            self.send_headers()


class HTTPConnection(object):
    
    bufsize = -1
    RequestHandlerClass = HTTPRequest
    environ = {"wsgi.version": (1, 0),
               "wsgi.url_scheme": "http",
               "wsgi.multithread": True,
               "wsgi.multiprocess": False,
               "wsgi.run_once": False,
               "wsgi.errors": sys.stderr,
               }
    
    def __init__(self, socket, addr, server):
        self.socket = socket
        self.addr = addr
        self.server = server
        
        self.rfile = self.socket.makefile("r", self.bufsize)
        self.wfile = self.socket.makefile("w", self.bufsize)
        
        # Copy the class environ into self.
        self.environ = self.environ.copy()
        self.environ.update({"wsgi.input": self.rfile,
                             "SERVER_NAME": self.server.server_name,
                             })
        
        if isinstance(self.server.bind_addr, basestring):
            # AF_UNIX. This isn't really allowed by WSGI, which doesn't
            # address unix domain sockets. But it's better than nothing.
            self.environ["SERVER_PORT"] = ""
        else:
            self.environ["SERVER_PORT"] = str(self.server.bind_addr[1])
            # optional values
            self.environ["REMOTE_HOST"] = self.addr[0]
            self.environ["REMOTE_ADDR"] = self.addr[0]
            self.environ["REMOTE_PORT"] = str(self.addr[1])
    
    def communicate(self):
        """Read each request and respond appropriately."""
        while True:
            req = self.RequestHandlerClass(self)
            # This order of operations should guarantee correct pipelining.
            req.parse_request()
            if not req.ready:
                break
            req.respond()
            if req.close_connection:
                break
    
    def close(self):
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
                conn = self.server.requests.get()
                if conn is _SHUTDOWNREQUEST:
                    return
                
                try:
                    try:
                        conn.communicate()
                    except socket.error, e:
                        errno = e.args[0]
                        if errno not in socket_errors_to_ignore:
                            traceback.print_exc()
                    except (KeyboardInterrupt, SystemExit), exc:
                        self.server.interrupt = exc
                    except:
                        traceback.print_exc()
                finally:
                    conn.close()
        except (KeyboardInterrupt, SystemExit), exc:
            self.server.interrupt = exc


class CherryPyWSGIServer(object):
    """An HTTP server for WSGI.
    
    bind_addr: a (host, port) tuple if TCP sockets are desired;
        for UNIX sockets, supply the filename as a string.
    wsgi_app: the WSGI 'application callable'; multiple WSGI applications
        may be passed as (script_name, callable) pairs.
    numthreads: the number of worker threads to create (default 10).
    server_name: the string to set for WSGI's SERVER_NAME environ entry.
        Defaults to socket.gethostname().
    max: the maximum number of queued requests (defaults to -1 = no limit).
    request_queue_size: the 'backlog' argument to socket.listen();
        specifies the maximum number of queued connections (default 5).
    timeout: the timeout in seconds for accepted connections (default 10).
    """
    
    protocol = "HTTP/1.1"
    version = "CherryPy/3.0.0alpha"
    ready = False
    _interrupt = None
    ConnectionClass = HTTPConnection
    
    def __init__(self, bind_addr, wsgi_app, numthreads=10, server_name=None,
                 max=-1, request_queue_size=5, timeout=10):
        self.requests = Queue.Queue(max)
        
        if callable(wsgi_app):
            # We've been handed a single wsgi_app, in CP-2.1 style.
            # Assume it's mounted at "".
            self.mount_points = [("", wsgi_app)]
        else:
            # We've been handed a list of (mount_point, wsgi_app) tuples,
            # so that the server can call different wsgi_apps, and also
            # correctly set SCRIPT_NAME.
            self.mount_points = wsgi_app
        self.mount_points.sort()
        self.mount_points.reverse()
        
        self.bind_addr = bind_addr
        self.numthreads = numthreads or 1
        if not server_name:
            server_name = socket.gethostname()
        self.server_name = server_name
        self.request_queue_size = request_queue_size
        self._workerThreads = []
        
        self.timeout = timeout
    
    def start(self):
        """Run the server forever."""
        # We don't have to trap KeyboardInterrupt or SystemExit here,
        # because cherrpy.server already does so, calling self.stop() for us.
        # If you're using this server with another framework, you should
        # trap those exceptions in whatever code block calls start().
        self._interrupt = None
        
        def bind(family, type, proto=0):
            """Create (or recreate) the actual socket object."""
            self.socket = socket.socket(family, type, proto)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(self.bind_addr)
        
        # Select the appropriate socket
        if isinstance(self.bind_addr, basestring):
            # AF_UNIX socket
            
            # So we can reuse the socket...
            try: os.unlink(self.bind_addr)
            except: pass
            
            # So everyone can access the socket...
            try: os.chmod(self.bind_addr, 0777)
            except: pass
            
            info = [(socket.AF_UNIX, socket.SOCK_STREAM, 0, "", self.bind_addr)]
        else:
            # AF_INET or AF_INET6 socket
            # Get the correct address family for our host (allows IPv6 addresses)
            host, port = self.bind_addr
            try:
                info = socket.getaddrinfo(host, port, socket.AF_UNSPEC,
                                          socket.SOCK_STREAM)
            except socket.gaierror:
                # Probably a DNS issue. Assume IPv4.
                info = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", self.bind_addr)]
        
        self.socket = None
        msg = "No socket could be created"
        for res in info:
            af, socktype, proto, canonname, sa = res
            try:
                bind(af, socktype, proto)
            except socket.error, msg:
                if self.socket:
                    self.socket.close()
                self.socket = None
                continue
            break
        if not self.socket:
            raise socket.error, msg
        
        # Timeout so KeyboardInterrupt can be caught on Win32
        self.socket.settimeout(1)
        self.socket.listen(self.request_queue_size)
        
        # Create worker threads
        for i in xrange(self.numthreads):
            self._workerThreads.append(WorkerThread(self))
        for worker in self._workerThreads:
            worker.setName("CP WSGIServer " + worker.getName())
            worker.start()
        for worker in self._workerThreads:
            while not worker.ready:
                time.sleep(.1)
        
        self.ready = True
        while self.ready:
            self.tick()
            if self.interrupt:
                while self.interrupt is True:
                    # Wait for self.stop() to complete
                    time.sleep(0.1)
                raise self.interrupt
    
    def tick(self):
        try:
            s, addr = self.socket.accept()
            if not self.ready:
                return
            if hasattr(s, 'settimeout'):
                s.settimeout(self.timeout)
            conn = self.ConnectionClass(s, addr, self)
            self.requests.put(conn)
        except socket.timeout:
            # The only reason for the timeout in start() is so we can
            # notice keyboard interrupts on Win32, which don't interrupt
            # accept() by default
            return
        except socket.error, x:
            if x.args[1] in ("Bad file descriptor",
                             "Socket operation on non-socket"):
                # Our socket was closed
                return
            raise
    
    def _get_interrupt(self):
        return self._interrupt
    def _set_interrupt(self, interrupt):
        self._interrupt = True
        self.stop()
        self._interrupt = interrupt
    interrupt = property(_get_interrupt, _set_interrupt)
    
    def stop(self):
        """Gracefully shutdown a server that is serving forever."""
        self.ready = False
        
        sock = getattr(self, "socket", None)
        if sock:
            if not isinstance(self.bind_addr, basestring):
                # Touch our own socket to make accept() return immediately.
                try:
                    host, port = sock.getsockname()[:2]
                except socket.error, x:
                    if x.args[1] != "Bad file descriptor":
                        raise
                else:
                    for res in socket.getaddrinfo(host, port, socket.AF_UNSPEC,
                                                  socket.SOCK_STREAM):
                        af, socktype, proto, canonname, sa = res
                        s = None
                        try:
                            s = socket.socket(af, socktype, proto)
                            # See http://groups.google.com/group/cherrypy-users/
                            #        browse_frm/thread/bbfe5eb39c904fe0
                            s.settimeout(1.0)
                            s.connect((host, port))
                            s.close()
                        except socket.error:
                            if s:
                                s.close()
            if hasattr(sock, "close"):
                sock.close()
            self.socket = None
        
        # Must shut down threads here so the code that calls
        # this method can know when all threads are stopped.
        for worker in self._workerThreads:
            self.requests.put(_SHUTDOWNREQUEST)
        
        # Don't join currentThread (when stop is called inside a request).
        current = threading.currentThread()
        while self._workerThreads:
            worker = self._workerThreads.pop()
            if worker is not current and worker.isAlive:
                try:
                    worker.join()
                except AssertionError:
                    pass

