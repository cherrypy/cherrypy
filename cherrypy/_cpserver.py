"""Manage an HTTP server with CherryPy."""

import socket
import threading
import time

import cherrypy
from cherrypy.lib import attributes


def client_host(server_host):
    """Return the host on which a client can connect to the given listener."""
    if server_host == '0.0.0.0':
        # 0.0.0.0 is INADDR_ANY, which should answer on localhost.
        return '127.0.0.1'
    if server_host == '::':
        # :: is IN6ADDR_ANY, which should answer on localhost.
        return '::1'
    return server_host


class Server(object):
    """Manager for a set of HTTP servers.
    
    This is both a container and controller for "HTTP server" objects,
    which are kept in Server.httpservers, a dictionary of the form:
    {httpserver: bind_addr} where 'bind_addr' is usually a (host, port)
    tuple.
    
    Most often, you will only be starting a single HTTP server. In this
    common case, you can set attributes (like socket_host and socket_port)
    on *this* object (which is probably cherrypy.server), and call
    quickstart. For example:
    
        cherrypy.server.socket_port = 80
        cherrypy.server.quickstart()
    
    But if you need to start more than one HTTP server (to serve on multiple
    ports, or protocols, etc.), you can manually register each one and then
    control them all through this object:
    
        s1 = MyWSGIServer(host='0.0.0.0', port=80)
        s2 = another.HTTPServer(host='localhost', SSL=True)
        cherrypy.server.httpservers = {s1: ('0.0.0.0', 80),
                                       s2: ('localhost', 443)}
        # Note we do not use quickstart when we define our own httpservers
        cherrypy.server.start()
    
    Whether you use quickstart(), or define your own httpserver entries and
    use start(), you'll find that the start, wait, restart, and stop methods
    work the same way, controlling all registered httpserver objects at once.
    """
    
    socket_port = 8080
    
    _socket_host = 'localhost'
    def _get_socket_host(self):
        return self._socket_host
    def _set_socket_host(self, value):
        if not value:
            raise ValueError("Host values of '' or None are not allowed. "
                             "Use '0.0.0.0' instead to listen on all active "
                             "interfaces (INADDR_ANY).")
        self._socket_host = value
    socket_host = property(_get_socket_host, _set_socket_host,
        doc="""The hostname or IP address on which to listen for connections.
        
        Host values may be any IPv4 or IPv6 address, or any valid hostname.
        The string 'localhost' is a synonym for '127.0.0.1' (or '::1', if
        your hosts file prefers IPv6). The string '0.0.0.0' is a special
        IPv4 entry meaning "any active interface" (INADDR_ANY), and '::'
        is the similar IN6ADDR_ANY for IPv6. The empty string or None are
        not allowed.""")
    
    socket_file = ''
    socket_queue_size = 5
    socket_timeout = 10
    shutdown_timeout = 5
    protocol_version = 'HTTP/1.1'
    reverse_dns = False
    thread_pool = 10
    max_request_header_size = 500 * 1024
    max_request_body_size = 100 * 1024 * 1024
    instance = None
    ssl_certificate = None
    ssl_private_key = None
    
    def __init__(self):
        self.httpservers = {}
        self.interrupt = None
    
    def quickstart(self, server=None):
        """Start from defaults. MUST be called from the main thread.
        
        This function works like CherryPy 2's server.start(). It loads and
        starts an httpserver based on the given server object (if provided)
        and attributes of self.
        """
        httpserver, bind_addr = self.httpserver_from_self(server)
        self.httpservers[httpserver] = bind_addr
        self.start()
    
    def httpserver_from_self(self, httpserver=None):
        """Return a (httpserver, bind_addr) pair based on self attributes."""
        if httpserver is None:
            httpserver = self.instance
        if httpserver is None:
            from cherrypy import _cpwsgi
            httpserver = _cpwsgi.CPWSGIServer()
        if isinstance(httpserver, basestring):
            httpserver = attributes(httpserver)()
        
        if self.socket_file:
            return httpserver, self.socket_file
        
        host = self.socket_host
        port = self.socket_port
        return httpserver, (host, port)
    
    def start(self):
        """Start all registered HTTP servers."""
        self.interrupt = None
        if not self.httpservers:
            raise ValueError("No HTTP servers have been created. "
                             "Try server.quickstart instead.")
        for httpserver in self.httpservers:
            self._start_http(httpserver)
        cherrypy.engine.subscribe('stop', self.stop)
    
    def _start_http(self, httpserver):
        """Start the given httpserver in a new thread."""
        scheme = "http"
        if getattr(httpserver, "ssl_certificate", None):
            scheme = "https"
        bind_addr = self.httpservers[httpserver]
        if isinstance(bind_addr, tuple):
            wait_for_free_port(*bind_addr)
            host, port = bind_addr
            on_what = "%s://%s:%s/" % (scheme, host, port)
        else:
            on_what = "socket file: %s" % bind_addr
        
        t = threading.Thread(target=self._start_http_thread, args=(httpserver,))
        t.setName("CPHTTPServer " + t.getName())
        t.start()
        
        self.wait(httpserver)
        cherrypy.log("Serving %s on %s" % (scheme.upper(), on_what), 'HTTP')
    
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
            cherrypy.log("<Ctrl-C> hit: shutting down HTTP servers", "SERVER")
            self.interrupt = exc
            cherrypy.engine.stop()
        except SystemExit, exc:
            cherrypy.log("SystemExit raised: shutting down HTTP servers", "SERVER")
            self.interrupt = exc
            cherrypy.engine.stop()
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
            while not (getattr(httpserver, "ready", False) or self.interrupt):
                time.sleep(.1)
            if self.interrupt:
                raise self.interrupt
            
            # Wait for port to be occupied
            if isinstance(bind_addr, tuple):
                host, port = bind_addr
                wait_for_occupied_port(host, port)
    
    def stop(self):
        """Stop all HTTP servers."""
        for httpserver, bind_addr in self.httpservers.items():
            try:
                httpstop = httpserver.stop
            except AttributeError:
                pass
            else:
                # httpstop() MUST block until the server is *truly* stopped.
                httpstop()
                if isinstance(bind_addr, tuple):
                    wait_for_free_port(*bind_addr)
                cherrypy.log("HTTP Server shut down", "HTTP")
    
    def restart(self):
        """Restart all HTTP servers."""
        self.stop()
        self.start()
    
    def base(self):
        """Return the base (scheme://host) for this server manager."""
        if self.socket_file:
            return self.socket_file
        
        host = self.socket_host
        if host in ('0.0.0.0', '::'):
            # 0.0.0.0 is INADDR_ANY and :: is IN6ADDR_ANY.
            # Look up the host name, which should be the
            # safest thing to spit out in a URL.
            host = socket.gethostname()
        
        port = self.socket_port
        
        if self.ssl_certificate:
            scheme = "https"
            if port != 443:
                host += ":%s" % port
        else:
            scheme = "http"
            if port != 80:
                host += ":%s" % port
        
        return "%s://%s" % (scheme, host)


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
    
    msg = "Port %s not free on %s" % (repr(port), repr(host))
    cherrypy.log(msg, 'HTTP')
    raise IOError(msg)

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
    
    msg = "Port %s not bound on %s" % (repr(port), repr(host))
    cherrypy.log(msg, 'HTTP')
    raise IOError(msg)
