import time

import cherrypy

import sessionconfig
from sessionerrors import SessionNotFoundError, SessionIncompatibleError
from ramsession import RamSession
from filesession import FileSession
from dbmsession import DBMSession

_sessionTypes = {
                  'ram'       : RamSession,
                  'file'      : FileSession,
                  'anydb'     : DBMSession
                }

try:
    # the user might not have sqlobject instaled
    from sqlobjectsession  import SQLObjectSession
    _sessionTypes['sqlobject'] = SQLObjectSession
except ImportError:
    pass


def _getSessions3():
    sessions = {}
    
    sessionLists = cherrypy.config.getAll('sessionFilter.sessionList')
    
    for sessionPath, sessionList in sessionLists.iteritems():
        if not isinstance(sessionList,list):
            sessionList=[sessionList]
        
        for index in xrange(len(sessionList)):
            session = sessionList[index]
            
            if isinstance(session, str):
                sessionName = session
                # check if the session is on or off
                if not cherrypy.config.get('sessionFilter.%s.on' % sessionName, True):
                    continue
                
                storageType = sessionconfig.retrieve('storageType', sessionName)
                
                sessionManager = _sessionTypes[storageType](sessionName)
                sessionManager.path = sessionPath
                sessionManager.lastCleanUp = time.time()
                
                sessionList[index] = sessionManager
                
                cherrypy.config.update({sessionPath: {'sessionFilter.sessionList' : sessionList} })
            else:
                sessionManager = session
            
            sessions[sessionManager.sessionName] = sessionManager
    
    return sessions

_getSessions2 = _getSessions3


class SessionFilter:
    """
    Input filter - get the sessionId (or generate a new one) and load up the session data
    """

    def __initSessions(self):
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
        sessionKeys = {}
        sessions = _getSessions2()
        for sessionName in sessions:
            sessionManager = sessions[sessionName]
            
            cookiePrefix = sessionconfig.retrieve('cookiePrefix', sessionName, None)
            cookieName = '%s_%s_%i' % (cookiePrefix, sessionName, hash(sessionManager))
            
            try:
                sessionKeys[sessionName] = cherrypy.request.simpleCookie[cookieName].value
            except:
                sessionKeys[sessionName] = None
        return sessionKeys
      
    def setSessionKey(self, sessionKey, sessionManager):
        """ 
        Sets the session key in a cookie.  Aplications should not call this function,
        but it might be usefull to redefine it.
        """
        
        sessionName = sessionManager.sessionName
        
        cookiePrefix = sessionconfig.retrieve('cookiePrefix', sessionName, None)
        cookieName = '%s_%s_%i' % (cookiePrefix, sessionName, hash(sessionManager))
        
        cherrypy.response.simpleCookie[cookieName] = sessionKey
        cherrypy.response.simpleCookie[cookieName]['version'] = 1
        
        cookiePath = sessionconfig.retrieve('cookiePath', sessionManager.sessionName, sessionManager.path)
        
        cherrypy.response.simpleCookie[cookieName]['path'] = cookiePath
    
    def __saveSessions(self):
        #sessions = _getSessions()
        sessions = _getSessions2()
        
        for sessionName in sessions:
            sessionManager = sessions[sessionName]
            sessionData = getattr(cherrypy.sessions, sessionName)
            sessionManager.commitCache(sessionData.key)
            sessionManager.cleanUpCache()
            
            sessionManager.lastCleanUp = time.time()
            
            cleanUpDelay = sessionconfig.retrieve('cleanUpDelay', sessionManager.sessionName)
            now = time.time()
            lastCleanUp = sessionManager.lastCleanUp
            if lastCleanUp + cleanUpDelay * 60 <= now:
                sessionManager.cleanUpOldSessions()
    
    def beforeMain(self):
        if (not cherrypy.config.get('staticFilter.on', False)
            and cherrypy.config.get('sessionFilter.on')):
           self.__initSessions()

    def beforeFinalize(self):
        if (not cherrypy.config.get('staticFilter.on', False)
            and cherrypy.config.get('sessionFilter.on')):
            self.__saveSessions()

    '''
    #this breaks a test case
    def beforeErrorResponse(self):
        # Still save session data
        if not cherrypy.config.get('staticFilter.on', False) and \
            cherrypy.config.get('sessionFilter.on'):
    '''
