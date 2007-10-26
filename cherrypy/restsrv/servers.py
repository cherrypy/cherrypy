"""Manage a set of HTTP servers."""

import socket
import threading
import time


class ServerManager(object):
    """Manager for a set of HTTP servers.
    
    This is both a container and controller for HTTP servers and gateways,
    which are kept in Server.httpservers, a dictionary of the form:
    {httpserver: bind_addr} where 'bind_addr' is usually a (host, port)
    tuple.
    
    If you need to start more than one HTTP server (to serve on multiple
    ports, or protocols, etc.), you can manually register each one and then
    control them all:
    
        s1 = MyWSGIServer(host='0.0.0.0', port=80)
        s2 = another.HTTPServer(host='127.0.0.1', SSL=True)
        server.httpservers = {s1: ('0.0.0.0', 80),
                              s2: ('127.0.0.1', 443)}
        server.start()
    
    The start, wait, restart, and stop methods control all registered
    httpserver objects at once.
    """
    
    
    def __init__(self, engine):
        self.engine = engine
        self.httpservers = {}
        self.interrupt = None
    
    def subscribe(self):
        self.engine.subscribe('start', self.start)
        self.engine.subscribe('stop', self.stop)
    
    def start(self):
        """Start all registered HTTP servers."""
        self.interrupt = None
        if not self.httpservers:
            raise ValueError("No HTTP servers have been created.")
        for httpserver in self.httpservers:
            self._start_http(httpserver)
    
    def _start_http(self, httpserver):
        """Start the given httpserver in a new thread."""
        bind_addr = self.httpservers[httpserver]
        if isinstance(bind_addr, tuple):
            wait_for_free_port(*bind_addr)
            host, port = bind_addr
            on_what = "%s:%s" % (host, port)
        else:
            on_what = "socket file: %s" % bind_addr
        
        t = threading.Thread(target=self._start_http_thread, args=(httpserver,))
        t.setName("HTTPServer " + t.getName())
        t.start()
        
        self.wait(httpserver)
        self.engine.log("Serving on %s" % on_what)
    
    def _start_http_thread(self, httpserver):
        """HTTP servers MUST be started in new threads, so that the
        main thread persists to receive KeyboardInterrupt's. If an
        exception is raised in the httpserver's thread then it's
        trapped here, and the engine (and therefore our httpservers)
        are shut down.
        """
        try:
            httpserver.start()
        except KeyboardInterrupt, exc:
            self.engine.log("<Ctrl-C> hit: shutting down HTTP servers")
            self.interrupt = exc
            self.engine.stop()
        except SystemExit, exc:
            self.engine.log("SystemExit raised: shutting down HTTP servers")
            self.interrupt = exc
            self.engine.stop()
            raise
        except:
            import sys
            self.interrupt = sys.exc_info()[1]
            self.engine.log("Error in HTTP server: shutting down",
                            traceback=True)
            self.engine.stop()
            raise
    
    def wait(self, httpserver=None):
        """Wait until the HTTP server is ready to receive requests.
        
        If no httpserver is specified, wait for all registered httpservers.
        """
        if httpserver is None:
            httpservers = self.httpservers.items()
        else:
            httpservers = [(httpserver, self.httpservers[httpserver])]
        
        for httpserver, bind_addr in httpservers:
            while not getattr(httpserver, "ready", False):
                if self.interrupt:
                    raise self.interrupt
                time.sleep(.1)
            
            # Wait for port to be occupied
            if isinstance(bind_addr, tuple):
                host, port = bind_addr
                wait_for_occupied_port(host, port)
    
    def stop(self):
        """Stop all HTTP servers."""
        for httpserver, bind_addr in self.httpservers.items():
            # httpstop() MUST block until the server is *truly* stopped.
            httpserver.stop()
            # Wait for the socket to be truly freed.
            if isinstance(bind_addr, tuple):
                wait_for_free_port(*bind_addr)
            self.engine.log("HTTP Server %s shut down" % httpserver)
    
    def restart(self):
        """Restart all HTTP servers."""
        self.stop()
        self.start()


def client_host(server_host):
    """Return the host on which a client can connect to the given listener."""
    if server_host == '0.0.0.0':
        # 0.0.0.0 is INADDR_ANY, which should answer on localhost.
        return '127.0.0.1'
    if server_host == '::':
        # :: is IN6ADDR_ANY, which should answer on localhost.
        return '::1'
    return server_host

def check_port(host, port):
    """Raise an error if the given port is not free on the given host."""
    if not host:
        raise ValueError("Host values of '' or None are not allowed.")
    host = client_host(host)
    port = int(port)
    
    # AF_INET or AF_INET6 socket
    # Get the correct address family for our host (allows IPv6 addresses)
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
            raise IOError("Port %s is in use on %s; perhaps the previous "
                          "httpserver did not shut down properly." %
                          (repr(port), repr(host)))
        except socket.error:
            if s:
                s.close()

def wait_for_free_port(host, port):
    """Wait for the specified port to become free (drop requests)."""
    if not host:
        raise ValueError("Host values of '' or None are not allowed.")
    
    for trial in xrange(50):
        try:
            check_port(host, port)
        except IOError:
            # Give the old server thread time to free the port.
            time.sleep(.1)
        else:
            return
    
    raise IOError("Port %r not free on %r" % (port, host))

def wait_for_occupied_port(host, port):
    """Wait for the specified port to become active (receive requests)."""
    if not host:
        raise ValueError("Host values of '' or None are not allowed.")
    
    for trial in xrange(50):
        try:
            check_port(host, port)
        except IOError:
            return
        else:
            time.sleep(.1)
    
    raise IOError("Port %r not bound on %r" % (port, host))
