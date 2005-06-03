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
import cpg, _cputil, _cphttptools, _cpthreadinglocal
from lib import autoreload


# Set some special attributes for adding hooks
onStartServerList = []
onStartThreadList = []
onStopServerList = []
onStopThreadList = []

def start(initOnly=False, serverClass=None):
    if cpg.config.get("server.environment") == "development":
        # Check initOnly. If True, we're probably not starting
        # our own webserver, and therefore could do Very Bad Things
        # when autoreload calls sys.exit.
        if not initOnly:
            autoreload.main(_start, (initOnly, serverClass))
            return
    
    _start(initOnly, serverClass)

def start(initOnly=False, serverClass=None):
    """
        Main function. All it does is this:
            - output config options
            - create response and request objects
            - starts a server
    """
    
    # Create request and response object (the same objects will be used
    #   throughout the entire life of the webserver)
    cpg.request = _cpthreadinglocal.local()
    cpg.response = _cpthreadinglocal.local()
    
    # Create threadData object as a thread-specific all-purpose storage
    cpg.threadData = _cpthreadinglocal.local()
    
    # Output config options (if cpg.config.get('server.logToScreen'))
    cpg.config.outputConfigMap()
    
    # Check the config options
    # TODO
    # _cpconfig.checkConfigOptions()
    
    # Initialize a few global variables
    cpg._lastCacheFlushTime = time.time()
    cpg._lastSessionCleanUpTime = time.time()
    cpg._sessionMap = {} # Map of "cookie" -> ("session object", "expiration time")
    
    # If sessions are stored in files and we
    # use threading, we need a lock on the file
    if (cpg.config.get('server.threadPool') > 1
        and cpg.config.get('session.storageType') == 'file'):
        cpg._sessionFileLock = threading.RLock()
    
    # Call the functions from cpg.server.onStartServerList
    for func in cpg.server.onStartServerList:
        func()
    
    if not initOnly:
        run_server(serverClass)

def run_server(serverClass=None):
    """Prepare the requested server and then run it."""
    
    # Instantiate the server.
    if serverClass is None:
        serverClass = cpg.config.get("server.class", None)
    if serverClass and isinstance(serverClass, basestring):
        serverClass = attributes(serverClass)
    if serverClass is None:
        import _cpwsgi
        serverClass = _cpwsgi.WSGIServer
    
    cpg._httpserver = serverClass()
    
    _cpLogMessage = _cputil.getSpecialFunction('_cpLogMessage')
    
    servingWhat = "HTTP"
    if cpg.config.get('server', 'socketPort'):
        onWhat = "socket: ('%s', %s)" % (cpg.config.get('server.socketHost'),
                                         cpg.config.get('server.socketPort'))
    else:
        onWhat = "socket file: %s" % cpg.config.get('server.socketFile')
    _cpLogMessage("Serving %s on %s" % (servingWhat, onWhat), 'HTTP')
    
    # Start the http server.
    try:
        cpg._httpserver.start()
    except (KeyboardInterrupt, SystemExit):
        _cpLogMessage("<Ctrl-C> hit: shutting down", "HTTP")
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

def request(clientAddress, remoteHost, requestLine, headers, rfile):
    threadID = threading._get_ident()
    if threadID not in seen_threads:
        i = len(seen_threads) + 1
        seen_threads[threadID] = i
        # Call the functions from cpg.server.onStartThreadList
        for func in cpg.server.onStartThreadList:
            func(i)
    return _cphttptools.Request(clientAddress, remoteHost,
                                requestLine, headers, rfile)

def stop():
    """Shutdown CherryPy (and any HTTP servers it started)."""
    try:
        httpstop = cpg._httpserver.stop
    except AttributeError:
        pass
    else:
        httpstop()
    
    # Call the functions from cpg.server.onStopThreadList
    for thread_ident, i in seen_threads.iteritems():
        for func in cpg.server.onStopThreadList:
            func(i)
    seen_threads.clear()
    
    # Call the functions from cpg.server.onStopServerList
    for func in cpg.server.onStopServerList:
        func()
