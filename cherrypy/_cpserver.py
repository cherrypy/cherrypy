"""Manage an HTTP server with CherryPy."""

import socket
import threading
import time

import cherrypy
from cherrypy.lib import attributes


class Server(object):
    """Manager for a set of HTTP servers."""
    
    def __init__(self):
        self.httpservers = {}
        self.interrupt = None
    
    def quickstart(self, server=None):
        """Main function for quick starts. MUST be called from the main thread.
        
        This function works like CherryPy 2's server.start(). It loads and
        starts an httpserver based on the given server object, if any, and
        config entries.
        """
        httpserver, bind_addr = self.httpserver_from_config(server)
        self.httpservers[httpserver] = bind_addr
        self.start()
    
    def httpserver_from_config(self, httpserver=None):
        """Return a (httpserver, bind_addr) pair based on config settings."""
        conf = cherrypy.config.get
        if httpserver is None:
            httpserver = conf('server.instance', None)
        if httpserver is None:
            from cherrypy import _cpwsgi
            httpserver = _cpwsgi.WSGIServer()
        if isinstance(httpserver, basestring):
            httpserver = attributes(httpserver)()
        
        if conf('server.socket_port'):
            host = conf('server.socket_host')
            port = conf('server.socket_port')
            if not host:
                host = 'localhost'
            return httpserver, (host, port)
        else:
            return httpserver, conf('server.socket_file')
    
    def start(self):
        """Start all registered HTTP servers."""
        self.interrupt = None
        for httpserver in self.httpservers:
            self._start_http(httpserver)
    
    def _start_http(self, httpserver):
        """Start the given httpserver in a new thread."""
        bind_addr = self.httpservers[httpserver]
        if isinstance(bind_addr, tuple):
            wait_for_free_port(*bind_addr)
            on_what = "http://%s:%s/" % bind_addr
        else:
            on_what = "socket file: %s" % bind_addr
        
        t = threading.Thread(target=self._start_http_thread, args=(httpserver,))
        t.setName("CPHTTPServer " + t.getName())
        t.start()
        
        self.wait(httpserver)
        cherrypy.log("Serving HTTP on %s" % on_what, 'HTTP')
    
    def _start_http_thread(self, httpserver):
        """HTTP servers MUST be started in new threads, so that the
        main thread persists to receive KeyboardInterrupt's. If an
        exception is raised in the httpserver's thread then it's
        trapped here, and the httpserver(s) and engine are shut down.
        """
        try:
            httpserver.start()
        except KeyboardInterrupt, exc:
            cherrypy.log("<Ctrl-C> hit: shutting down HTTP servers", "SERVER")
            self.interrupt = exc
            self.stop()
            cherrypy.engine.stop()
        except SystemExit, exc:
            cherrypy.log("SystemExit raised: shutting down HTTP servers", "SERVER")
            self.interrupt = exc
            self.stop()
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
                wait_for_occupied_port(*bind_addr)
    
    def stop(self):
        """Stop all HTTP server(s)."""
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
        """Restart the HTTP server."""
        self.stop()
        self.start()


def check_port(host, port):
    """Raise an error if the given port is not free on the given host."""
    if not host:
        host = 'localhost'
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
        host = 'localhost'
    
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
        host = 'localhost'
    
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
