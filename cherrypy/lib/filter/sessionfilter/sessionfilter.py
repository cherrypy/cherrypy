
import cherrypy.cpg

import time

from sessionerrors import SessionNotFoundError, SessionIncompatibleError

import sessionconfig 
from cherrypy._cputil import getObjectTrail
def _getSessions3():
    cpg = cherrypy.cpg
    sessions = {}
    
    sessionLists = cpg.config.getAll('sessionFilter.sessionsList')

    for sessionPath, sessionList in sessionLists.iteritems():
        if not isinstance(sessionList,list):
            sessionList=[sessionList]
        for index in xrange(len(sessionList)):
            session = sessionList[index]
            
            if isinstance(session, str):
                sessionName = session
                # check if the session is on or off
                if not cpg.config.get('sessionFilter.%s.on' % sessionName, True):
                    continue

                storageType = sessionconfig.retrieve('storageType', sessionName)
                
                sessionManager = sessionconfig._sessionTypes[storageType](sessionName)
                sessionManager.path = sessionPath
                sessionManager.lastCleanUp = time.time()

                sessionList[index] = sessionManager
                
                cpg.config.update({sessionPath: {'sessionFilter.sessionsList' : sessionList} })
            else:
                if not cpg.config.get('sessionFilter.%s.on' % session, True):
                    continue
                
                sessionManager = session
                sessionManager.lastCleanUp = time.time()

                cleanUpDelay = sessionconfig.retrieve('cleanUpDelay', sessionManager.sessionName)
                now = time.time()
                lastCleanUp = sessionManager.lastCleanUp
                if lastCleanUp + cleanUpDelay * 60 <= now:
                    sessionManager.cleanUpOldSessions()

            sessions[sessionManager.sessionName] = sessionManager

    return sessions
    
_getSessions2 = _getSessions3

class SessionFilter:
    """
    Input filter - get the sessionId (or generate a new one) and load up the session data
    """

    def __initSessions(self):
        cpg = cherrypy.cpg
        sessions = _getSessions2()
#        sessions = _getSessions()
        sessionKeys = self.getSessionKeys()
        
        for sessionName in sessions:
            sessionManager = sessions[sessionName]
            sessionKey = sessionKeys.get(sessionName, None)
            try:
               sessionManager.loadSession(sessionKey)
            except SessionNotFoundError:
               newKey = sessionManager.createSession()
               sessionManager.loadSession(newKey)
               
               self.setSessionKey(newKey, sessionManager) 
                
    def getSessionKeys(self):
        """ 
        Returns the all current sessionkeys as a dict
        """
        cpg = cherrypy.cpg
        
        sessionKeys= {}
        sessions = _getSessions2()
        for sessionName in sessions:
            sessionManager = sessions[sessionName]

            cookiePrefix = sessionconfig.retrieve('cookiePrefix', sessionName, None)
            
            cookieName = '%s_%s_%i' % (cookiePrefix, sessionName, hash(sessionManager))
            
            try:
                sessionKeys[sessionName] = cpg.request.simpleCookie[cookieName].value
            except:
                sessionKeys[sessionName] = None
        return sessionKeys
      

    def setSessionKey(self, sessionKey, sessionManager):
        """ 
        Sets the session key in a cookie.  Aplications should not call this function,
        but it might be usefull to redefine it.
        """

        cpg = cherrypy.cpg
        
        sessionName = sessionManager.sessionName
        
        cookiePrefix = sessionconfig.retrieve('cookiePrefix', sessionName, None)
        
        cookieName = '%s_%s_%i' % (cookiePrefix, sessionName, hash(sessionManager))

        cpg.response.simpleCookie[cookieName] = sessionKey
        cpg.response.simpleCookie[cookieName]['version'] = 1
        
        cookiePath = sessionconfig.retrieve('cookiePath', sessionManager.sessionName, sessionManager.path)
        
        cpg.response.simpleCookie[cookieName]['path'] = cookiePath

    
    def __saveSessions(self):
        cpg = cherrypy.cpg
        #sessions = _getSessions()
        sessions = _getSessions2()
        
        for sessionName in sessions:
            sessionManager = sessions[sessionName]
            sessionData = getattr(cpg.sessions, sessionName)
            sessionManager.commitCache(sessionData.key)
    
    def beforeMain(self):
        cpg = cherrypy.cpg
        if not cpg.config.get('staticFilter.on', False) and \
            cpg.config.get('sessionFilter.on'):
           self.__initSessions()

    def beforeFinalize(self):
        cpg = cherrypy.cpg
        if not cpg.config.get('staticFilter.on', False) and \
            cpg.config.get('sessionFilter.on'):
            self.__saveSessions()

    '''
    #this breaks a test case
    def beforeErrorResponse(self):
        cpg = cherrypy.cpg
        # Still save session data
        if not cpg.config.get('staticFilter.on', False) and \
            cpg.config.get('sessionFilter.on'):
    '''
