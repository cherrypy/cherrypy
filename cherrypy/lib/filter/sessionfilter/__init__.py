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


_sessionTypes = {
                  'ram'       : RamAdaptor,
                  'file'      : FileAdaptor,
                  'anydb'     : DBMAdaptor
                }

try:
    # the user might not have sqlobject instaled
    from sqlobjectadaptor import SQLObjectSession
    _sessionTypes['sqlobject'] = SQLObjectSession
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

    def __init__(self):
        """ Initilizes the session filter and creates cherrypy.sessions  """

        self.__localData= local()
        
        self.sessionManagers = {}
        cherrypy.config.update(_sessionDefaults, override = False)
        
        self.__initSessionManagers()

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
            try:
                if sessionName in self.sessionManagers:
                    raise DuplicateSessionError()
            except KeyError:
                pass
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
    
    def __initSessionManagers(self):
        for section, settings in cherrypy.config.configMap.iteritems():
            for setting, value in settings.iteritems():
                if not setting.startswith('sessionFilter'):
                    continue

                keySplit = setting.split('.')
                if len(keySplit) == 2:
                    sessionName = 'default'
                else:
                    sessionName = keySplit[1]
                
                if keySplit[-1] != 'on' or value == False:
                    continue

                if section == 'global':
                    path = '/'
                else:
                    path = section

                if sessionName not in self.sessionManagers:
                    sessionManager = self.__newSessionManager(sessionName, path)
                    # create a new local instance
                    setattr(sessionManager, 'settings', local())

                    self.sessionManagers[sessionName] = sessionManager
    
    def __loadConfigData(self, sessionName):
            sessionManager = self.sessionManagers[sessionName]
            
            settings = {}
            for settingName in _sessionSettingNames:
                default = cherrypy.config.get('sessionFilter.%s' % settingName)
                value = cherrypy.config.get('sessionFilter.%s.%s' % (sessionName, settingName), default)
                settings[settingName] = value
                
                setattr(sessionManager.settings, settingName, value)
                
    def __loadSessions(self):
        
        # look up all of the session keys by cookie
        
        for sessionName, sessionManager in self.sessionManagers.iteritems():
            if not cherrypy.config.get('sessionFilter.%s.on' % sessionName, False):
                continue

            self.__loadConfigData(sessionName)
            cookieName = sessionManager.cookieName
            
            try:
                sessionKey = cherrypy.request.simpleCookie[cookieName].value
            except KeyError:
                sessionKey = sessionManager.createSession()
                self.setSessionKey(sessionKey, sessionManager) 
                sessionManager.loadSession(sessionKey)

            try:
                sessionManager.loadSession(sessionKey)
            except SessionNotFoundError:
                sessionKey = sessionManager.createSession()
                self.setSessionKey(sessionKey, sessionManager)  
                sessionManager.loadSession(sessionKey)

    def setSessionKey(self, sessionKey, sessionManager):
        """ 
        Sets the session key in a cookie. 
        """
        
        sessionName = sessionManager.name
        cookieName  = sessionManager.cookieName
        
        
        # if we do not have a manually defined cookie path use path where the session
        # manager was defined
        try:
            cookiePath = self.settings.cookiePath
        except AttributeError:
            cookiePath = sessionManager.path

        timeout = sessionManager.settings.timeout
        
        cherrypy.response.simpleCookie[cookieName] = sessionKey
        cherrypy.response.simpleCookie[cookieName]['path'] = cookiePath
        cherrypy.response.simpleCookie[cookieName]['max-age'] = timeout*60
        
        # try and set the cookie domain
        try:
            cookieDomain = self.settings.cookieDomain
            cherrypy.response.simpleCookie[cookieName]['domain'] = cookieDomain
        except AttributeError:
            pass

        # try and set a cookie comment
        try:
            cookieComment = self.settings.cookieComment
            cherrypy.response.simpleCookie[cookieName]['comment'] = cookieComment
        except AttributeError:
            pass

    def __saveSessions(self):
        
        for sessionName, sessionManager in self.sessionManagers.iteritems():
            if not cherrypy.config.get('sessionFilter.%s.on' % sessionName, False):
                continue

            sessionData = getattr(cherrypy.session, sessionName)
            sessionManager.commitCache(sessionData.key)
            sessionManager.cleanUpCache()
            
            sessionManager.cleanUpOldSessions()

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
