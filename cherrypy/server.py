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

"""
Main CherryPy module:
    - Creates a server
"""

import cgi
import threading
import time
import warnings

import cherrypy
from cherrypy import _cphttptools
from cherrypy.lib import autoreload, profiler


# Set some special attributes for adding hooks
onStartServerList = []
onStartThreadList = []
onStopServerList = []
onStopThreadList = []


_missing = object()

def start(initOnly=False, serverClass=_missing):
    """Main function. MUST be called from the main thread.
    
    Set initOnly to True to keep this function from blocking.
    Set serverClass to None to skip starting any HTTP server.
    """
    # This duplicates the line in start_app_server on purpose.
    cherrypy._appserver_state = None
    cherrypy._interrupt = None
    
    conf = cherrypy.config.get
    
    if serverClass is _missing:
        serverClass = conf("server.class", _missing)
    if serverClass is _missing:
        import _cpwsgi
        serverClass = _cpwsgi.WSGIServer
    elif serverClass and isinstance(serverClass, basestring):
        # Dynamically load the class from the given string
        serverClass = cherrypy._cputil.attributes(serverClass)
    
    # Autoreload, but check serverClass. If None, we're not starting
    # our own webserver, and therefore could do Very Bad Things when
    # autoreload calls sys.exit.
    if serverClass is not None:
        defaultOn = (conf("server.environment") == "development")
        if conf('autoreload.on', defaultOn):
            try:
                autoreload.main(_start, (initOnly, serverClass))
            except KeyboardInterrupt:
                cherrypy.log("<Ctrl-C> hit: shutting down autoreloader", "HTTP")
            return
    
    _start(initOnly, serverClass)

def _start(initOnly, serverClass):
    # This duplicates the line in start_app_server on purpose.
    cherrypy._appserver_state = None
    
    cherrypy._httpserverclass = serverClass
    conf = cherrypy.config.get
    
    try:
        if cherrypy.codecoverage:
            from cherrypy.lib import covercp
            covercp.start()
        
        # Output config options to log
        if conf("server.logConfigOptions", True):
            cherrypy.config.outputConfigMap()
        # TODO: config.checkConfigOptions()
        
        # If sessions are stored in files and we
        # use threading, we need a lock on the file
        if (conf('server.threadPool') > 1
            and conf('session.storageType') == 'file'):
            cherrypy._sessionFileLock = threading.RLock()
        
        # set cgi.maxlen which will limit the size of POST request bodies
        cgi.maxlen = conf('server.maxRequestSize')
        
        # Set up the profiler if requested.
        if conf("profiling.on", False):
            ppath = conf("profiling.path", "")
            cherrypy.profiler = profiler.Profiler(ppath)
        else:
            cherrypy.profiler = None
        
        # Initialize the built in filters
        cherrypy._cputil._cpInitDefaultFilters()
        cherrypy._cputil._cpInitUserDefinedFilters()
        
        start_app_server()
        start_http_server()
        wait_until_ready()
        
        if not initOnly:
            # Block forever (wait for KeyboardInterrupt or SystemExit).
            while True:
                time.sleep(.1)
                if cherrypy._interrupt:
                    raise cherrypy._interrupt
    except KeyboardInterrupt:
        cherrypy.log("<Ctrl-C> hit: shutting down server", "HTTP")
        stop()
    except SystemExit:
        cherrypy.log("SystemExit raised: shutting down server", "HTTP")
        stop()

def start_app_server():
    """Start the CherryPy core."""
    # Use a flag to indicate the state of the cherrypy application server.
    # 0 = Not started
    # None = In process of starting
    # 1 = Started, ready to receive requests
    cherrypy._appserver_state = None
    
    # Call the functions from cherrypy.server.onStartServerList
    for func in cherrypy.server.onStartServerList:
        func()
    
    cherrypy._appserver_state = 1

def start_http_server(serverClass=None):
    """Start the requested HTTP server."""
    if serverClass is None:
        serverClass = cherrypy._httpserverclass
    if serverClass is None:
        return
    
    if cherrypy._httpserver is not None:
        msg = ("You seem to have an HTTP server still running."
               "Please call cherrypy.server.stop_http_server() "
               "before continuing.")
        warnings.warn(msg)
    
    if cherrypy.config.get('server.socketPort'):
        host = cherrypy.config.get('server.socketHost')
        port = cherrypy.config.get('server.socketPort')
        
        wait_for_free_port(host, port)
        
        if not host:
            host = 'localhost'
        onWhat = "http://%s:%s/" % (host, port)
    else:
        onWhat = "socket file: %s" % cherrypy.config.get('server.socketFile')
    cherrypy.log("Serving HTTP on %s" % onWhat, 'HTTP')
    
    # Instantiate the server.
    cherrypy._httpserver = serverClass()
    
    # HTTP servers MUST be started in a new thread, so that the
    # main thread persists to receive KeyboardInterrupt's. This
    # wrapper traps an interrupt in the http server's main thread
    # and shutdowns CherryPy.
    def _start_http():
        try:
            cherrypy._httpserver.start()
        except (KeyboardInterrupt, SystemExit), exc:
            cherrypy._interrupt = exc
    threading.Thread(target=_start_http).start()


seen_threads = {}

def request(clientAddress, remoteHost, requestLine, headers, rfile, scheme="http"):
    """request(clientAddress, remoteHost, requestLine, headers, rfile, scheme="http")
    
    clientAddress: the (IP address, port) of the client
    remoteHost: the IP address of the client
    requestLine: "<HTTP method> <url?qs> HTTP/<version>",
            e.g. "GET /main?abc=123 HTTP/1.1"
    headers: a list of (key, value) tuples
    rfile: a file-like object from which to read the HTTP request body
    scheme: either "http" or "https"; defaults to "http"
    """
    if cherrypy._appserver_state == 0:
        raise cherrypy.NotReady("No thread has called cherrypy.server.start().")
    elif cherrypy._appserver_state == None:
        raise cherrypy.NotReady("cherrypy.server.start() encountered errors.")
    
    threadID = threading._get_ident()
    if threadID not in seen_threads:
        
        if cherrypy.codecoverage:
            from cherrypy.lib import covercp
            covercp.start()
        
        i = len(seen_threads) + 1
        seen_threads[threadID] = i
        # Call the functions from cherrypy.server.onStartThreadList
        for func in cherrypy.server.onStartThreadList:
            func(i)
    
    if cherrypy.profiler:
        cherrypy.profiler.run(_cphttptools.Request, clientAddress, remoteHost,
                              requestLine, headers, rfile, scheme)
    else:
        _cphttptools.Request(clientAddress, remoteHost,
                             requestLine, headers, rfile, scheme)

def stop():
    """Stop CherryPy and any HTTP servers it started."""
    stop_http_server()
    stop_app_server()

def stop_app_server():
    """Stop CherryPy."""
    cherrypy._appserver_state = 0
    cherrypy.log("CherryPy shut down", "HTTP")

def stop_http_server():
    """Stop the HTTP server."""
    try:
        httpstop = cherrypy._httpserver.stop
    except AttributeError:
        pass
    else:
        # httpstop() MUST block until the server is *truly* stopped.
        httpstop()
        cherrypy.log("HTTP Server shut down", "HTTP")
    
    # Call the functions from cherrypy.server.onStopThreadList
    for thread_ident, i in seen_threads.iteritems():
        for func in cherrypy.server.onStopThreadList:
            func(i)
    seen_threads.clear()
    
    # Call the functions from cherrypy.server.onStopServerList
    for func in cherrypy.server.onStopServerList:
        func()
    
    cherrypy._httpserver = None

def restart():
    """Restart CherryPy (and any HTTP servers it started)."""
    stop()
    start_app_server()
    start_http_server()
    wait_until_ready()

def wait_until_ready():
    """Block the caller until CherryPy is ready to receive requests."""
    
    # Wait for app to start up
    while cherrypy._appserver_state != 1:
        time.sleep(.1)
    
    # Wait for HTTP server to start up
    if cherrypy._httpserverclass is not None:
        while not getattr(cherrypy._httpserver, "ready", None):
            time.sleep(.1)
        
        # Wait for port to be occupied
        if cherrypy.config.get('server.socketPort'):
            host = cherrypy.config.get('server.socketHost')
            port = cherrypy.config.get('server.socketPort')
            wait_for_occupied_port(host, port)

def check_port(host, port):
    """Raise an error if the given port is not free on the given host."""
    
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, int(port)))
        s.close()
        raise IOError("Port %s is in use on %s; perhaps the previous "
                      "server did not shut down properly." % (port, host))
    except socket.error:
        pass

def wait_for_free_port(host, port):
    """Wait for the specified port to become free (drop requests)."""
    for trial in xrange(50):
        try:
            check_port(host, port)
        except IOError:
            # Give the old server thread time to free the port.
            time.sleep(.1)
        else:
            return
    
    cherrypy.log("Port %s not free" % port, 'HTTP')
    raise cherrypy.NotReady("Port not free.")

def wait_for_occupied_port(host, port):
    """Wait for the specified port to become active (receive requests)."""
    for trial in xrange(50):
        try:
            check_port(host, port)
        except IOError:
            return
        else:
            time.sleep(.1)
    
    cherrypy.log("Port %s not bound" % port, 'HTTP')
    raise cherrypy.NotReady("Port not bound.")

def start_with_callback(func, args=None, kwargs=None, serverClass=_missing):
    """Start CherryPy, then callback the given func in a new thread."""
    if args is None:
        args = ()
    if kwargs is None:
        kwargs = {}
    args = (func,) + args
    threading.Thread(target=_callback_intermediary, args=args, kwargs=kwargs).start()
    cherrypy.server.start(serverClass=serverClass)

def _callback_intermediary(func, *args, **kwargs):
    wait_until_ready()
    func(*args, **kwargs)
