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

import warnings
import threading
import time

import cherrypy
from cherrypy import _cphttptools
from cherrypy.lib import autoreload, profiler


# Set some special attributes for adding hooks
onStartServerList = []
onStartThreadList = []
onStopServerList = []
onStopThreadList = []


def start(initOnly=False, serverClass=None):
    defaultOn = (cherrypy.config.get("server.environment") == "development")
    if cherrypy.config.get('autoreload.on', defaultOn):
        # Check initOnly. If True, we're probably not starting
        # our own webserver, and therefore could do Very Bad Things
        # when autoreload calls sys.exit.
        if not initOnly:
            try:
                autoreload.main(_start, (initOnly, serverClass))
            except KeyboardInterrupt:
                cherrypy.log("<Ctrl-C> hit: shutting down autoreloader", "HTTP")
            return
    
    _start(initOnly, serverClass)

def _start(initOnly=False, serverClass=None):
    """Main function."""
    try:
        if cherrypy.codecoverage:
            from cherrypy.lib import covercp
            covercp.start()
        
        # Use a flag to indicate the state of the cherrypy application server.
        # 0 = Not started
        # None = In process of starting
        # 1 = Started, ready to receive requests
        cherrypy._appserver_state = None
        
        # Output config options to log
        if cherrypy.config.get("server.logConfigOptions", True):
            cherrypy.config.outputConfigMap()
        
        # Check the config options
        # TODO
        # config.checkConfigOptions()
        
        # If sessions are stored in files and we
        # use threading, we need a lock on the file
        if (cherrypy.config.get('server.threadPool') > 1
            and cherrypy.config.get('session.storageType') == 'file'):
            cherrypy._sessionFileLock = threading.RLock()
        
        # set cgi.maxlen which will limit the size of POST request bodies
        import cgi
        cgi.maxlen = cherrypy.config.get('server.maxRequestSize')
        
        # Call the functions from cherrypy.server.onStartServerList
        for func in cherrypy.server.onStartServerList:
            func()
        
        # Set up the profiler if requested.
        if cherrypy.config.get("profiling.on", False):
            ppath = cherrypy.config.get("profiling.path", "")
            cherrypy.profiler = profiler.Profiler(ppath)
        else:
            cherrypy.profiler = None

        # Initilize the built in filters
        cherrypy._cputil._cpInitDefaultFilters()
        cherrypy._cputil._cpInitUserDefinedFilters()
        
        if initOnly:
            cherrypy._appserver_state = 1
        else:
            run_server(serverClass)
    except:
        # _start may be called as the target of a Thread, in which case
        # any errors would pass silently. Log them at least.
        cherrypy.log(cherrypy._cputil.formatExc())
        raise


def run_server(serverClass=None):
    """Prepare the requested server and then run it."""
    if cherrypy._httpserver is not None:
        warnings.warn("You seem to have an HTTP server still running."
                      "Please call cherrypy.server.stop() before continuing.")
    
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
    if serverClass is None:
        serverClass = cherrypy.config.get("server.class", None)
    if serverClass and isinstance(serverClass, basestring):
        serverClass = cherrypy._cputil.attributes(serverClass)
    if serverClass is None:
        import _cpwsgi
        serverClass = _cpwsgi.WSGIServer
    cherrypy._httpserver = serverClass()
    
    # Start the http server. Must be done after wait_for_free_port (above).
    # Note that _httpserver.start() will block this thread, so there
    # isn't any notification in this thread that the HTTP server is
    # truly ready. See wait_until_ready() for all the things that
    # other threads should wait for before proceeding with requests.
    try:
        cherrypy._appserver_state = 1
        # This should block until the http server stops.
        cherrypy._httpserver.start()
    except KeyboardInterrupt:
        cherrypy.log("<Ctrl-C> hit: shutting down server", "HTTP")
        stop()
    except SystemExit:
        cherrypy.log("SystemExit raised: shutting down server", "HTTP")
        stop()


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
    """Shutdown CherryPy (and any HTTP servers it started)."""
    try:
        httpstop = cherrypy._httpserver.stop
    except AttributeError:
        pass
    else:
        # httpstop() should block until the server is *truly* stopped.
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
    cherrypy._appserver_state = 0
    cherrypy.log("CherryPy shut down", "HTTP")

def restart():
    """Stop and start CherryPy."""
    http = getattr(cherrypy, '_httpserver', None)
    stop()
    if http:
        # Start the server in a new thread
        thread_args = {"serverClass": http.__class__}
        t = threading.Thread(target=_start, kwargs=thread_args)
        t.start()
    else:
        _start(initOnly=True)
    wait_until_ready()

def wait_until_ready():
    """Block the caller until CherryPy is ready to receive requests."""
    
    while cherrypy._appserver_state != 1:
        time.sleep(.1)
    
    http = getattr(cherrypy, '_httpserver', None)
    if http:
        # Wait for HTTP server to start up
        while not http.ready:
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
