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
    'sessionFilter.cacheTimeout' : 0
}

from sessionerrors import SessionNotFoundError, SessionIncompatibleError, SessionBadStorageTypeError, SessionConfigError, DuplicateSessionError
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
                if self.sessionManagers[storageType].path != sessionPath:
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
    
    def __pathIter(self):
        path = cherrypy.request.path.rstrip('/')
        i = path.rfind("/")
        pathList=[path]
        while 0 < i:
            path = path[:i]
            pathList.append(path)
            i=path.rfind('/')
        pathList.append('/')
        return reversed(pathList)

    def __loadConfigData(self):
        try:
            path = cherrypy.request.path
        except AttributeError:
            path = "/"
            
        configMap = cherrypy.config.configMap
        
        configData = {}
        self.__localData.activeSessions = []
        
        for path in self.__pathIter():
            # cut index off the end of the pass
            if path.endswith('/index'):
                path = path[0:-5]
            
            # set the section 
            if path == '/':
                section = 'global'
            else:
                section = path
            
            # will will place all of the config data here as we read it
            sectionData = {}
            
            # get the current settings or return an empty dictionary
            settings = cherrypy.config.configMap.get(section, {})
            
            # iterate over all of the settings for the current path
            for key, value in settings.iteritems():
                # make sure this is a session setting
                if key.startswith('sessionFilter.'):
                    sectionData = configData.setdefault(section, {})
                    keySplit = key.split('.')
                    
                    # if the key has 1 '.' then it is a default setting
                    if len(keySplit) == 2:
                        # we use None as the key for default settings
                        # and we place the key, value in the dictionary

                        # because we iterate from / down to the current node
                        # we will automatically overwite any default values
                        # if they are redefined by child nodes
                        defaults = configData.setdefault(None, {})
                        defaults[keySplit[1]] = value
                    
                    # if the key has 3 '.' then it is a named session
                    elif len(keySplit) == 3:
                        currentSession = sectionData.setdefault(keySplit[1], {})
                        currentSession[keySplit[2]] = value
            
            # we now iterate back over the settings and
            # locate/initilize the session manager
            for session, settings in sectionData.iteritems():
                if not settings['on']:
                    continue
                try:
                    sessionManager = self.sessionManagers[session]
                except KeyError:
                    sessionManager = self.__newSessionManager(session, path)
                    self.sessionManagers[session] = sessionManager
                
                # create a new local instance
                setattr(sessionManager, 'settings', local())
                
                # set all of the default settings
                for key, value in configData.get(None, {}).iteritems():
                    setattr(sessionManager.settings, key, value)
                
                # set all of settings
                for key, value in settings.iteritems():
                    setattr(sessionManager.settings, key, value)

                # add this to the list of active session managers
                self.__localData.activeSessions.append(sessionManager)
    
    def __initSessions(self):
        
        # look up all of the session keys by cookie
        self.__loadConfigData()
        
        sessionKeys = self.getSessionKeys()

        for sessionManager in self.__localData.activeSessions:
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
        
        for sessionManager in self.__localData.activeSessions:
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
        
        for sessionManager in self.__localData.activeSessions:
            sessionName = sessionManager.name
            
            sessionData = getattr(cherrypy.session, sessionName)
            sessionManager.commitCache(sessionData.key)
            sessionManager.cleanUpCache()
            
            now = time.time()
            if sessionManager.nextCleanUp < now:
                sessionManager.cleanUpOldSessions()
                cleanUpDelay = sessionManager.settings.cleanUpDelay
                sessionManager.nextCleanUp=now + cleanUpDelay * 60

        # this isn't needed but may be helpfull for debugging
#        self.configData = None
    
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
