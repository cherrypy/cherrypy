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
A module containing a few utility classes/functions used by CherryPy
"""

import time, thread, os
import cPickle as pickle
import cpg

def _cpLogMessage(msg, context = '', severity = 0):
    """ Default method for logging messages """

    nowTuple = time.localtime(time.time())
    nowStr = '%04d/%02d/%02d %02d:%02d:%02d' % (nowTuple[:6])
    if severity == 0:
        level = "INFO"
    elif severity == 1:
        level = "WARNING"
    elif severity == 2:
        level = "ERROR"
    else:
        lebel = "UNKNOWN"
    try:
        logToScreen = int(cpg.config.get('server.logToScreen', cast='bool'))
    except:
        logToScreen = True
    s = nowStr + ' ' + context + ' ' + level + ' ' + msg
    if logToScreen:
        print s
    if cpg.config.get('server.logFile'):
        f = open(cpg.config.get('server.logFile'), 'ab')
        f.write(s + '\n')
        f.close()

def _cpOnError():
    """ Default _cpOnError method """

    import traceback, StringIO
    bodyFile = StringIO.StringIO()
    traceback.print_exc(file = bodyFile)
    cpg.response.body = [bodyFile.getvalue()]
    cpg.response.headerMap['Content-Type'] = 'text/plain'

def _cpSaveSessionData(sessionId, sessionData, expirationTime,
        threadPool = None, sessionStorageType = None,
        sessionStorageFileDir = None):
    """ Save session data if needed """

    if threadPool is None:
        threadPool = cpg.config.get('server.threadPool', cast='int')
    if sessionStorageType is None:
        sessionStorageType = cpg.config.get('session.storageType')
    if sessionStorageFileDir is None:
        sessionStorageFileDir = cpg.config.get('session.storageFileDir')

    t = time.localtime(expirationTime)
    if sessionStorageType == 'file':
        fname=os.path.join(sessionStorageFileDir,sessionId)
        if threadPool > 1:
            cpg._sessionFileLock.acquire()
        f = open(fname,"wb")
        pickle.dump((sessionData, expirationTime), f)
        f.close()
        if threadPool > 1:
            cpg._sessionFileLock.release()

    elif sessionStorageType=="ram":
        # Update expiration time
        cpg._sessionMap[sessionId] = (sessionData, expirationTime)

def _cpLoadSessionData(sessionId, threadPool = None, sessionStorageType = None,
        sessionStorageFileDir = None):
    """ Return the session data for a given sessionId.
        The _expirationTime will be checked by the caller of this function
    """

    if threadPool is None:
        threadPool = cpg.config.get('server.threadPool', cast='int')
    if sessionStorageType is None:
        sessionStorageType = cpg.config.get('session.storageType')
    if sessionStorageFileDir is None:
        sessionStorageFileDir = cpg.config.get('session.storageFileDir')

    if sessionStorageType == "ram":
        if cpg._sessionMap.has_key(sessionId):
            return cpg._sessionMap[sessionId]
        else: return None

    elif sessionStorageType == "file":
        fname = os.path.join(sessionStorageFileDir, sessionId)
        if os.path.exists(fname):
            if threadPool > 1:
                cpg._sessionFileLock.acquire()
            f = open(fname, "rb")
            sessionData = pickle.load(f)
            f.close()
            if threadPool > 1:
                cpg._sessionFileLock.release()
            return sessionData
        else: return None

def _cpCleanUpOldSessions(threadPool = None, sessionStorageType = None,
        sessionStorageFileDir = None):
    """ Clean up old sessions """

    if threadPool is None:
        threadPool = cpg.config.get('server.threadPool', cast='int')
    if sessionStorageType is None:
        sessionStorageType = cpg.config.get('session.storageType')
    if sessionStorageFileDir is None:
        sessionStorageFileDir = cpg.config.get('session.storageFileDir')

    # Clean up old session data
    now = time.time()
    if sessionStorageType == "ram":
        sessionIdToDeleteList = []
        for sessionId, (dummy, expirationTime) in cpg._sessionMap.items():
            if expirationTime < now:
                sessionIdToDeleteList.append(sessionId)
        for sessionId in sessionIdToDeleteList:
            del cpg._sessionMap[sessionId]

    elif sessionStorageType=="file":
        # This process is very expensive because we go through all files, parse them and then delete them if the session is expired
        # One optimization would be to just store a list of (sessionId, expirationTime) in *one* file
        sessionFileList = os.listdir(sessionStorageFileDir)
        for sessionId in sessionFileList:
            try:
                dummy, expirationTime = _cpLoadSessionData(sessionId)
                if expirationTime < now:
                    os.remove(os.path.join(sessionStorageFileDir, sessionId))
            except:
                pass

    elif sessionStorageType == "cookie":
        # Nothing to do in this case: the session data is stored on the client
        pass

_cpFilterList = []

# Filters that are always included
from cherrypy.lib.filter import baseurlfilter, cachefilter, \
    decodingfilter, encodingfilter, gzipfilter, logdebuginfofilter, \
    staticfilter, tidyfilter, virtualhostfilter, xmlrpcfilter
_cpDefaultInputFilterList = [
    cachefilter.CacheInputFilter(),
    logdebuginfofilter.LogDebugInfoInputFilter(),
    virtualhostfilter.VirtualHostFilter(),
    baseurlfilter.BaseUrlFilter(),
    decodingfilter.DecodingFilter(),
    staticfilter.StaticFilter(),
    xmlrpcfilter.XmlRpcInputFilter(),
]
_cpDefaultOutputFilterList = [
    xmlrpcfilter.XmlRpcOutputFilter(),
    encodingfilter.EncodingFilter(),
    tidyfilter.TidyFilter(),
    logdebuginfofilter.LogDebugInfoOutputFilter(),
    gzipfilter.GzipFilter(),
    cachefilter.CacheOutputFilter(),
]

