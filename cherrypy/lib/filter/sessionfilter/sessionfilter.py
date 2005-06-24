
import cherrypy.cpg

import time

from sessionerrors import SessionNotFoundError, SessionIncompatibleError

import sessionconfig 
from cherrypy._cputil import getObjectTrail

def _getSessions2():
    cpg =cherrypy.cpg
    sessions = {}

    objectTrail = getObjectTrail()
    
    for n in xrange(len(objectTrail)):
        obj = objectTrail[n]
        objPath = '/'.join(cpg.request.path.split('/')[0:n+1])
        if not objPath:
            objPath = '/'

        try:
            sessionList = obj._cpSessionList
        except AttributeError:
            
            if obj == cpg:
                obj._cpSessionList = [{'sessionName':'default'}]
                sessionList = obj._cpSessionList
            else:
                sessionList = []
            
        for sessionIndex in xrange(len(sessionList)):
            sessionManager = sessionList[sessionIndex]
            

            if isinstance(sessionManager, dict):
                # must be initilized
                sessionName   = sessionManager['sessionName']
                compatible    = sessionManager.get('compatible',  [])
                incompatible  = sessionManager.get('icompatible', [])
               
                # unless it is off initilize
                if cpg.config.get('sessionFilter.%s.on' % sessionName, True):
                    
                    storageType = sessionconfig.retrieve('storageType', sessionName)
    
                    if compatible and not storageType in compatible or \
                       incompatible and not storageType in incompatible:
                        raise SessionIncompatibleError
                    
                    sessionManager = sessionconfig._sessionTypes[storageType](sessionName)
                    sessionManager.lastCleanUp = time.time()
                    sessionManager.path = objPath
    
                    obj._cpSessionList[sessionIndex] = sessionManager

            elif isinstance(sessionManager, str):
                # unless it is off initilize
                if cpg.config.get('sessionFilter.%s.on' % sessionManager, True):
                    storageType = sessionconfig.retrieve('storageType', sessionManager)
                    sessionManager = sessionconfig._sessionTypes[storageType](sessionManager)
                    sessionManager.lastCleanUp = time.time()
                    
                    sessionManager.path = objPath
                    obj._cpSessionList[sessionIndex] = sessionManager
                
            
            else: # try and clean up
                cleanUpDelay = sessionconfig.retrieve('cleanUpDelay', sessionManager.sessionName)
                now = time.time()
                lastCleanUp = sessionManager.lastCleanUp
                if lastCleanUp + cleanUpDelay * 60 <= now:
                    sessionManager.cleanUpOldSessions()
            
            sessions[sessionManager.sessionName] = sessionManager
    
    return sessions

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

            cookiePrefix = sessionconfig.retrieve('cookieName', sessionName, None)
            
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
        
        cookiePrefix = sessionconfig.retrieve('cookieName', sessionName, None)
        
        cookieName = '%s_%s_%i' % (cookiePrefix, sessionName, hash(sessionManager))

        cpg.response.simpleCookie[cookieName] = sessionKey
        cpg.response.simpleCookie[cookieName]['version'] = 1
        
        cpg.response.simpleCookie[cookieName]['path'] = sessionManager.path

    
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
