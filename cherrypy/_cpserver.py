"""Manage an HTTP server with CherryPy."""

import threading
import time

import cherrypy
from cherrypy.lib import attributes


class Server(object):
    """Manager for an HTTP server."""
    
    def __init__(self):
        self.httpserver = None
        self.interrupt = None
    
    def start(self, server=None):
        """Main function. MUST be called from the main thread."""
        self.interrupt = None
        
        conf = cherrypy.config.get
        if server is None:
            server = conf('server.instance', None)
        if server is None:
            import _cpwsgi
            server = _cpwsgi.WSGIServer()
        if isinstance(server, basestring):
            server = attributes(server)()
        self.httpserver = server
        
        if conf('server.socket_port'):
            host = conf('server.socket_host')
            port = conf('server.socket_port')
            wait_for_free_port(host, port)
            if not host:
                host = 'localhost'
            on_what = "http://%s:%s/" % (host, port)
        else:
            on_what = "socket file: %s" % conf('server.socket_file')
        
        # HTTP servers MUST be started in a new thread, so that the
        # main thread persists to receive KeyboardInterrupt's. If an
        # exception is raised in the http server's thread then it's
        # trapped here, and the http server and engine are shut down.
        def _start_http():
            try:
                self.httpserver.start()
            except KeyboardInterrupt, exc:
                cherrypy.log("<Ctrl-C> hit: shutting down HTTP server", "SERVER")
                self.interrupt = exc
                self.stop()
                cherrypy.engine.stop()
            except SystemExit, exc:
                cherrypy.log("SystemExit raised: shutting down HTTP server", "SERVER")
                self.interrupt = exc
                self.stop()
                cherrypy.engine.stop()
                raise
        t = threading.Thread(target=_start_http)
        t.setName("CPHTTPServer " + t.getName())
        t.start()
        
        self.wait()
        cherrypy.log("Serving HTTP on %s" % on_what, 'HTTP')
    
    def wait(self):
        """Wait until the HTTP server is ready to receive requests."""
        while (not getattr(self.httpserver, "ready", False)
               and not self.interrupt):
            time.sleep(.1)
        if self.interrupt:
            raise self.interrupt
        
        # Wait for port to be occupied
        if cherrypy.config.get('server.socket_port'):
            host = cherrypy.config.get('server.socket_host')
            port = cherrypy.config.get('server.socket_port')
            wait_for_occupied_port(host, port)
    
    def stop(self):
        """Stop the HTTP server."""
        try:
            httpstop = self.httpserver.stop
        except AttributeError:
            pass
        else:
            # httpstop() MUST block until the server is *truly* stopped.
            httpstop()
            conf = cherrypy.config.get
            if conf('server.socket_port'):
                host = conf('server.socket_host')
                port = conf('server.socket_port')
                wait_for_free_port(host, port)
            cherrypy.log("HTTP Server shut down", "HTTP")
    
    def restart(self):
        """Restart the HTTP server."""
        self.stop()
        self.interrupt = None
        self.start()


def check_port(host, port):
    """Raise an error if the given port is not free on the given host."""
    sock_file = cherrypy.config.get('server.socket_file')
    if sock_file:
        return
    
    if not host:
        host = 'localhost'
    port = int(port)
    
    import socket
    
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
                          "server did not shut down properly." %
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
