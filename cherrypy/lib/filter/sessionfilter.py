"""
Copyright (c) 2005, CherryPy Team (team@cherrypy.org)
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

from basefilter import BaseFilter
import random, sha, string, time
alphanum = string.letters + string.digits


class SessionFilter(BaseFilter):
    
    def onStartResource(self):
        # We have to dynamically import cpg because Python can't handle
        #   circular module imports :-(
        global cpg, _cputil
        from cherrypy import cpg, _cputil
        cpg.threadData.sessionFilterOn = False
    
    def beforeMain(self):
        cpg.threadData.sessionFilterOn = bool(cpg.config.get('session.storageType'))
        if cpg.threadData.sessionFilterOn:
            cleanupSessionData()
            if not cpg.request.isStatic:
                getSessionData()
    
    def beforeFinalize(self):
        if cpg.threadData.sessionFilterOn and not cpg.request.isStatic:
            saveSessionData()
    
    def beforeErrorResponse(self):
        # Still save session data
        if cpg.threadData.sessionFilterOn and not cpg.request.isStatic:
            saveSessionData()


def getSessionData():
    now = time.time()
    cookieName = cpg.config.get('session.cookieName')
    
    # First, get sessionId from cookie
    try:
        sessionId = cpg.request.simpleCookie[cookieName].value
    except:
        sessionId = None
    
    if sessionId:
        # Load session data from wherever it was stored
        sessionData = _cputil.getSpecialFunction('_cpLoadSessionData')(sessionId)
        if sessionData is None:
            sessionId = None
        else:
            cpg.request.sessionMap, expirationTime = sessionData
            if now > expirationTime:
                # Session expired
                sessionId = None
    
    # Create a new sessionId if needed
    if not sessionId:
        sessionId = generateSessionId()
        cpg.request.sessionMap = {'_sessionId': sessionId}
        
        cpg.response.simpleCookie[cookieName] = sessionId
        cpg.response.simpleCookie[cookieName]['path'] = '/'
        cpg.response.simpleCookie[cookieName]['version'] = 1

def generateSessionId():
    s = "%s%s" % (random.random(), time.time())
    return sha.sha(s).hexdigest()

def cleanupSessionData():
    """Clean up expired sessions if needed."""
    now = time.time()
    delay = cpg.config.get('session.cleanUpDelay')
    if delay and (cpg._lastSessionCleanUpTime + (delay * 60) <= now):
        cpg._lastSessionCleanUpTime = now
        _cputil.getSpecialFunction('_cpCleanUpOldSessions')()

def saveSessionData():
    sessionId = cpg.request.sessionMap['_sessionId']
    timeout = cpg.config.get('session.timeout')
    expire = (time.time() + (timeout * 60))
    savefunc = _cputil.getSpecialFunction('_cpSaveSessionData')
    savefunc(sessionId, cpg.request.sessionMap, expire)
