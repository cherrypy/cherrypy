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


class SessionFilter:
    """
    Input filter - get the sessionId (or generate a new one) and load up the session data
    """

    def __init__(self):
        """ Initilizes the session filter and creates cherrypy.sessions  """

        try:
            from threading import local
        except ImportError:
            from cherrypy._cpthreadinglocal import local

        # Create as sessions object for accessing session data
        cherrypy.sessions = local()


    def __newSessionManager(self, sessionName, sessionPath):
        """ 
        Takes the name of a new session and its configuration path.
        Returns a storageAdaptor instance maching the configured storage type.
        If the storage type is not built in, it tries to use sessionFilter.storageAadaptors.
        If the storage type still can not be found, an exception is raised.
        """
        # look up the storage type or return the default
        storageType = sessionconfig.retrieve('storageType', sessionName)
        
        # try to initilize a built in session
        try:
            storageAdaptor = _sessionTypes[storageType]
        except KeyError:
            # the storageType is not built in
            
            # check for custom storage adaptors
            adaptors = cherrypy.config.get('sessionFilter.storageAdaptors')
            try:
                storageAdaptor = adaptors[storageType]
            except cherrypy.InternalError:
                # we couldn't find the session
                raise SessionBadStorageTypeError(storageType)
        
        return storageAdaptor(sessionName, sessionPath)        
        
    # this function gets all active sessions based on the path
    def __getSessions(self):
        """
        Returns a list containing instances of all active sessions for the current request path.
        """
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
                    if not cherrypy.config.get('sessionFilter.%s.on' % session, True):
                        continue
                    sessionManager = self.__newSessionManager(session, sessionPath)
                    
                    # now we replace the string name with the instanced storage class
                    # thanks to references this will directly change the configMap
                    sessionList[index] = sessionManager
                    
                else:
                    sessionManager = session
                
                sessions.append(sessionManager)
        
        return sessions



    def __initSessions(self):
        
        # look up all of the session keys by cookie
        sessionKeys = self.getSessionKeys()
        
        for sessionManager in self.__getSessions():
            sessionKey = sessionKeys.get(sessionManager.name, None)
            
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
        
        for sessionManager in self.__getSessions():
            sessionName = sessionManager.name
            cookieName  = sessionManager.cookieName

            try:
                sessionKeys[sessionName] = cherrypy.request.simpleCookie[cookieName].value
            except:
                sessionKeys[sessionName] = None
        return sessionKeys
      
    def setSessionKey(self, sessionKey, sessionManager):
        """ 
        Sets the session key in a cookie. 
        """
        
        sessionName = sessionManager.name
        cookieName  = sessionManager.cookieName
        
        
        # if we do not have a manually defined cookie path use path where the session
        # manager was defined
        cookiePath = sessionconfig.retrieve('cookiePath', sessionManager.name, sessionManager.path)
        timeout = sessionconfig.retrieve('timeout', sessionManager.name)
        
        cherrypy.response.simpleCookie[cookieName] = sessionKey
        cherrypy.response.simpleCookie[cookieName]['path'] = cookiePath
        cherrypy.response.simpleCookie[cookieName]['max-age'] = timeout*60
        
    def __saveSessions(self):
        
        for sessionManager in self.__getSessions():
            sessionName = sessionManager.name
            
            sessionData = getattr(cherrypy.sessions, sessionName)
            sessionManager.commitCache(sessionData.key)
            sessionManager.cleanUpCache()
            
            sessionManager.lastCleanUp = time.time()
            
            cleanUpDelay = sessionconfig.retrieve('cleanUpDelay', sessionManager.name)
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
