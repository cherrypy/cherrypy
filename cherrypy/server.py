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

import threading
import time
import sys

import cherrypy
from cherrypy import _cphttptools
from cherrypy.lib import autoreload, profiler, covercp


# Set some special attributes for adding hooks
onStartServerList = []
onStartThreadList = []
onStopServerList = []
onStopThreadList = []


def start(initOnly=False, serverClass=None):
    if cherrypy.config.get("server.environment") == "development":
        # Check initOnly. If True, we're probably not starting
        # our own webserver, and therefore could do Very Bad Things
        # when autoreload calls sys.exit.
        if not initOnly:
            autoreload.main(_start, (initOnly, serverClass))
            return
    
    _start(initOnly, serverClass)

def _start(initOnly=False, serverClass=None):
    """
        Main function. All it does is this:
            - output config options
            - create response and request objects
            - starts a server
            - initilizes built in filters
    """
    
    if cherrypy.codecoverage:
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
    
    # Initialize a few global variables
    cherrypy._lastCacheFlushTime = time.time()
    cherrypy._lastSessionCleanUpTime = time.time()
    cherrypy._sessionMap = {} # Map of "cookie" -> ("session object", "expiration time")
    
    # If sessions are stored in files and we
    # use threading, we need a lock on the file
    if (cherrypy.config.get('server.threadPool') > 1
        and cherrypy.config.get('session.storageType') == 'file'):
        cherrypy._sessionFileLock = threading.RLock()
    
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
    
    if initOnly:
        cherrypy._appserver_state = 1
    else:
        run_server(serverClass)

def run_server(serverClass=None):
    """Prepare the requested server and then run it."""
    
    if cherrypy._httpserver is not None:
        warnings.warn("You seem to have an HTTP server still running."
                      "Please call cherrypy.server.stop() before continuing.")
    
    # Instantiate the server.
    if serverClass is None:
        serverClass = cherrypy.config.get("server.class", None)
    if serverClass and isinstance(serverClass, basestring):
        serverClass = attributes(serverClass)
    if serverClass is None:
        import _cpwsgi
        serverClass = _cpwsgi.WSGIServer
    
    cherrypy._httpserver = serverClass()
    
    if cherrypy.config.get('server', 'socketPort'):
        onWhat = ("socket: ('%s', %s)"
                  % (cherrypy.config.get('server.socketHost'),
                     cherrypy.config.get('server.socketPort')))
    else:
        onWhat = "socket file: %s" % cherrypy.config.get('server.socketFile')
    cherrypy.log("Serving HTTP on %s" % onWhat, 'HTTP')
    
    # Start the http server.
    try:
        cherrypy._appserver_state = 1
        cherrypy._httpserver.start()
    except (KeyboardInterrupt, SystemExit):
        cherrypy.log("<Ctrl-C> hit: shutting down", "HTTP")
        stop()

def modules(modulePath):
    """Load a module and retrieve a reference to that module."""
    try:
        aMod = sys.modules[modulePath]
        if aMod is None:
            raise KeyError
    except KeyError:
        # The last [''] is important.
        aMod = __import__(modulePath, globals(), locals(), [''])
    return aMod

def attributes(fullAttributeName):
    """Load a module and retrieve an attribute of that module."""
    
    # Parse out the path, module, and attribute
    lastDot = fullAttributeName.rfind(u".")
    attrName = fullAttributeName[lastDot + 1:]
    modPath = fullAttributeName[:lastDot]
    
    aMod = modules(modPath)
    # Let an AttributeError propagate outward.
    try:
        anAttr = getattr(aMod, attrName)
    except AttributeError:
        raise AttributeError("'%s' object has no attribute '%s'"
                             % (modPath, attrName))
    
    # Return a reference to the attribute.
    return anAttr


seen_threads = {}

def request(clientAddress, remoteHost, requestLine, headers, rfile, scheme="http"):
    """request(clientAddress, remoteHost, requestLine, headers, rfile, scheme="http")
    
    clientAddress: the IP address of the client
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
        httpstop()
    
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
