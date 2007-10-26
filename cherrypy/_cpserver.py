"""Manage HTTP servers with CherryPy."""

import socket

import cherrypy
from cherrypy.lib import attributes
from cherrypy.restsrv.servers import *


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
    
    If you want to use an HTTP server other than the default, create it
    and pass it to quickstart:
    
        s = MyCustomWSGIServer(wsgiapp, port=8080)
        cherrypy.server.quickstart(s)
    
    But if you need to start more than one HTTP server (to serve on multiple
    ports, or protocols, etc.), you can manually register each one and then
    control them all:
    
        s1 = MyWSGIServer(host='0.0.0.0', port=80)
        s2 = another.HTTPServer(host='127.0.0.1', SSL=True)
        cherrypy.server.httpservers = {s1: ('0.0.0.0', 80),
                                       s2: ('127.0.0.1', 443)}
        # Note we do not use quickstart when we define our own httpservers
        cherrypy.server.start()
    
    Whether you use quickstart(), or define your own httpserver entries and
    use start(), you'll find that the start, wait, restart, and stop methods
    work the same way, controlling all registered httpserver objects at once.
    """
    
    socket_port = 8080
    
    _socket_host = '127.0.0.1'
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
        self.mgr = ServerManager(cherrypy.engine)
    
    def _get_httpservers(self):
        return self.mgr.httpservers
    def _set_httpservers(self, value):
        self.mgr.httpservers = value
    httpservers = property(_get_httpservers, _set_httpservers)
    
    def quickstart(self, server=None):
        """Start from defaults. MUST be called from the main thread.
        
        This function works like CherryPy 2's server.start(). It loads and
        starts an httpserver based on the given server object (if provided)
        and attributes of self.
        """
        httpserver, bind_addr = self.httpserver_from_self(server)
        self.mgr.httpservers[httpserver] = bind_addr
        self.mgr.start()
        cherrypy.engine.subscribe('stop', self.mgr.stop)
    
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
        self.mgr.start()
    
    def wait(self, httpserver=None):
        """Wait until the HTTP server is ready to receive requests.
        
        If no httpserver is specified, wait for all registered httpservers.
        """
        self.mgr.wait(httpserver)
    
    def stop(self):
        """Stop all HTTP servers."""
        self.mgr.stop()
    
    def restart(self):
        """Restart all HTTP servers."""
        self.mgr.restart()
    
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

