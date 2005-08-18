import time

import cherrypy

_sessionDefaults = {
    'sessionFilter.on' : False,
    'sessionFilter.sessionList' : ['default'],
    'sessionFilter.storageAdaptors' : {},
    'sessionFilter.timeout': 60,
    'sessionFilter.cleanUpDelay': 60,
    'sessionFilter.storageType' : 'ram',
    'sessionFilter.cookiePrefix': 'CherryPySession',
    'sessionFilter.storagePath': '.sessiondata',
    'sessionFilter.dbFile': 'sessionData.db',
    'sessionFilter.default.on': True,
    'sessionFilter.cacheTimeout' : 0,
    'sessionFilter.timeMultiple' : 60
}

_sessionSettingNames = []

for key in _sessionDefaults:
    _sessionSettingNames.append(key.split('.')[-1])
    

from sessionerrors import SessionNotFoundError, SessionIncompatibleError, SessionBadStorageTypeError, SessionConfigError, DuplicateSessionError
from ramadaptor import RamAdaptor
from fileadaptor import FileAdaptor
from anydbadaptor import DBMAdaptor

sessionTypes = {
                  'ram'       : RamAdaptor,
                  'file'      : FileAdaptor,
                  'anydb'     : DBMAdaptor
                }

try:
    # the user might not have sqlobject instaled
    from sqlobjectadaptor import SQLObjectSession
    sessionTypes['sqlobject'] = SQLObjectSession
except ImportError:
    pass

try:
    from threading import local
except ImportError:
    from cherrypy._cpthreadinglocal import local


class SessionFilter:
    """
    Input filter - get the sessionId (or generate a new one) and load up the session data
    """

    def __init__(self, sessionName = 'default', sessionPath = '/'):
        """ Initilizes the session filter and creates cherrypy.sessions  """

        self.__localData= local()
        
        cherrypy.config.update(_sessionDefaults, override = False)
        self.sessionManager = self.__newSessionManager(sessionName, sessionPath)
    def __newSessionManager(self, sessionName, sessionPath):
        """
        Takes the name of a new session and its configuration path.
        Returns a storageAdaptor instance maching the configured storage type.
        If the storage type is not built in, it tries to use sessionFilter.storageAadaptors.
        If the storage type still can not be found, an exception is raised.
        """
        # look up the storage type or return the default
        storageType = cherrypy.config.get('sessionFilter.%s.storageType' % sessionName, None)
        if not storageType:
            storageType = cherrypy.config.get('sessionFilter.storageType')
        
        # try to initilize a built in session
        try:
            storageAdaptor = sessionTypes[storageType]
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
    
    
    def __loadSessions(self):
        # look up all of the session keys by cookie
        sessionManager = self.sessionManager
        sessionName = sessionManager.name
        
        if not cherrypy.config.get('sessionFilter.%s.on' % sessionName, False):
            return

        cookieName = sessionManager.cookieName
        
        try:
            sessionKey = cherrypy.request.simpleCookie[cookieName].value
        except KeyError:
            sessionKey = sessionManager.createSession()
            self.saveSessionDictKey(sessionKey) 
            sessionManager.loadSession(sessionKey)

        try:
            sessionManager.loadSession(sessionKey)
        except SessionNotFoundError:
            sessionKey = sessionManager.createSession()
            self.saveSessionDictKey(sessionKey)
            sessionManager.loadSession(sessionKey)

    def saveSessionDictKey(self, sessionKey):
        """ 
        Sets the session key in a cookie. 
        """
        
        sessionManager = self.sessionManager

        sessionName = sessionManager.name
        cookieName  = sessionManager.cookieName
        
        
        # if we do not have a manually defined cookie path use path where the session
        # manager was defined
        cookiePath = sessionManager.getSetting('cookiePath', sessionManager.path)

        timeout = sessionManager.getSetting('timeout')
        
        cherrypy.response.simpleCookie[cookieName] = sessionKey
        cherrypy.response.simpleCookie[cookieName]['path'] = cookiePath
        cherrypy.response.simpleCookie[cookieName]['max-age'] = timeout*60
        
        # try and set the cookie domain
        try:
            cookieDomain = sessionManager.getSetting('cookieDomain')
            cherrypy.response.simpleCookie[cookieName]['domain'] = cookieDomain
        except AttributeError:
            pass

        # try and set a cookie comment
        try:
            cookieComment = sessionManager.getSetting('cookieComment')
            cherrypy.response.simpleCookie[cookieName]['comment'] = cookieComment
        except AttributeError:
            pass

    def __saveSessions(self):
        try:
            sessionData = getattr(cherrypy.session, self.sessionManager.name)
        
            self.sessionManager.commitCache(sessionData.key)
            self.sessionManager.cleanUpCache()

            self.sessionManager.cleanUpOldSessions()
        except AttributeError:
            return
        
    def beforeMain(self):
        if (not cherrypy.config.get('staticFilter.on', False)
            and cherrypy.config.get('sessionFilter.on')):
           self.__loadSessions()

    def beforeFinalize(self):
        if (not cherrypy.config.get('staticFilter.on', False)
            and cherrypy.config.get('sessionFilter.on')):
            self.__saveSessions()

    def beforeErrorResponse(self):
        # Still save session data
        if not cherrypy.config.get('staticFilter.on', False) and \
            cherrypy.config.get('sessionFilter.on'):
            self.__saveSessions()
