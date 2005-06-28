import time

import cherrypy

import sessionconfig

from sessionerrors import SessionNotFoundError, SessionIncompatibleError, SessionBadStorageTypeError
from ramadaptor import RamSession
from fileadaptor import FileSession
from anydbadaptor import DBMSession

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


# this function gets all active sessions based on the path
def _getSessions():
    sessions = []
    
    sessionLists = cherrypy.config.getAll('sessionFilter.sessionList')
    
    # loop across all paths with session listts
    for sessionPath, sessionList in sessionLists.iteritems():
        
        # if it isn't a list make it one
        if not isinstance(sessionList,list):
            sessionList=[sessionList]
        
        for index in xrange(len(sessionList)):
            
            session = sessionList[index]
            
            # check if the session is a string, if it is
            # try and match it to a storage adaptor and replace
            # the string in the list with the initilized adaptor
            if isinstance(session, str):
                sessionName = session
                # if the session is off skip to the next session in the list
                if not cherrypy.config.get('sessionFilter.%s.on' % sessionName, True):
                    continue
                
                # look up the storage type or return the default
                storageType = sessionconfig.retrieve('storageType', sessionName)
                
                # try to initilize a built in session
                try:
                    sessionManager = _sessionTypes[storageType](sessionName)
                except KeyError:
                    # the storageType is not built in
                    try:
                        sessionManger = cherrypy._cputil.getSpecialAttribute(storageType)(sessionName)
                    except cherrypy.InternalError:
                        # it is not a built in session and the adaptor has not been
                        # set as an attribute in the CherryPy tree
                        raise SessionBadStorageTypeError(storageType)
                        
                
                # we need to remember the path
                sessionManager.path = sessionPath

                # the session is born clean
                sessionManager.lastCleanUp = time.time()
                
                # replace the entry in the session list
                sessionList[index] = sessionManager
                
                # put then new session list back in the config map
                cherrypy.config.update({sessionPath: {'sessionFilter.sessionList' : sessionList} })
            else:
                sessionManager = session
            
            sessions.append(sessionManager)
    
    return sessions

class SessionFilter:
    """
    Input filter - get the sessionId (or generate a new one) and load up the session data
    """

    def __initSessions(self):
        
        # look up all of the session keys by cookie
        sessionKeys = self.getSessionKeys()
        
        for sessionManager in _getSessions():
            sessionName = sessionManager.sessionName
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
        
        for sessionManager in _getSessions():
            sessionName = sessionManager.sessionName
            
            cookiePrefix = sessionconfig.retrieve('cookiePrefix', sessionName, None)
            cookieName = '%s_%s_%i' % (cookiePrefix, sessionName, hash(sessionManager))
            
            try:
                sessionKeys[sessionName] = cherrypy.request.simpleCookie[cookieName].value
            except:
                sessionKeys[sessionName] = None
        return sessionKeys
      
    def setSessionKey(self, sessionKey, sessionManager):
        """ 
        Sets the session key in a cookie. 
        """
        
        sessionName = sessionManager.sessionName
        
        cookiePrefix = sessionconfig.retrieve('cookiePrefix', sessionName, None)
        cookieName = '%s_%s_%i' % (cookiePrefix, sessionName, hash(sessionManager))
        
        cherrypy.response.simpleCookie[cookieName] = sessionKey
        cherrypy.response.simpleCookie[cookieName]['version'] = 1
        
        # if we do not have a manually defined cookie path use path where the session
        # manager was defined
        cookiePath = sessionconfig.retrieve('cookiePath', sessionManager.sessionName, sessionManager.path)
        
        cherrypy.response.simpleCookie[cookieName]['path'] = cookiePath
    
    def __saveSessions(self):
        
        for sessionManager in _getSessions():
            sessionName = sessionManager.sessionName
            
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

    #this breaks a test case
    def beforeErrorResponse(self):
        # Still save session data
        if not cherrypy.config.get('staticFilter.on', False) and \
            cherrypy.config.get('sessionFilter.on'):
            self.__saveSessions()
