import time

import cherrypy

_sessionDefaults = {
    'sessionFilter.on' : False,
    'sessionFilter.sessionList' : ['default'],
    'sessionFilter.storageAdaptors' : {},
    'sessionFilter.timeout': 60,
    'sessionFilter.cleanUpDelay': 60,
    'sessionFilter.storageType' : 'ram',
    'sessionFilter.cookieName': 'CherryPySession',
    'sessionFilter.cookiePath'  : '/',
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
        
        cherrypy.config.update(_sessionDefaults, override = False)
        
        # look up the storage type or return the default
        storageType = cherrypy.config.get('sessionFilter.storageType', None)
        
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
        
        self.sessionManager = storageAdaptor()
    
    
    def __loadSession(self):
        """ loads the session or creates a new one """
        sessionManager = self.sessionManager
        
        cookieName = cherrypy.config.get('sessionFilter.cookieName')
        
        try:
            sessionKey = cherrypy.request.simpleCookie[cookieName].value
        except KeyError:
            sessionKey = sessionManager.createSession()
            self.sessionManager.loadSession(sessionKey)

        try:
            self.sessionManager.loadSession(sessionKey)
        except SessionNotFoundError:
            sessionKey = sessionManager.createSession()
            self.sessionManager.loadSession(sessionKey)
        
        # currently we have to keep setting the cookie to update the timeout value
        self.setSessionCookie(sessionKey)  

    def setSessionCookie(self, sessionKey):
        """ 
        Sets the session key in a cookie. 
        """

        sessionManager = self.sessionManager
        
        cookieName  = cherrypy.config.get('sessionFilter.cookieName')
        
        cookiePath = cherrypy.config.get('sessionFilter.cookiePath')

        timeout = cherrypy.config.get('sessionFilter.timeout')
        
        cherrypy.response.simpleCookie[cookieName] = sessionKey
        cherrypy.response.simpleCookie[cookieName]['path'] = cookiePath
        cherrypy.response.simpleCookie[cookieName]['max-age'] = timeout*60
        
        # try and set the cookie domain
        cookieDomain = cherrypy.config.get('sessionFilter.cookieDomain')
        if cookieDomain:
            cherrypy.response.simpleCookie[cookieName]['domain'] = cookieDomain

        # try and set a cookie comment
        cookieComment = cherrypy.config.get('sessionFilter.cookieComment')
        if cookieComment:
            cherrypy.response.simpleCookie[cookieName]['comment'] = cookieComment

    def __saveSessions(self):
        try:
            #sessionData = getattr(cherrypy.session, 'default')
            sessionData = cherrypy.session._getDict()
        
            self.sessionManager.commitCache(sessionData.key)
            self.sessionManager.cleanUpCache()

            self.sessionManager.cleanUpOldSessions()
        except AttributeError:
            return
        
    def beforeMain(self):
        if (not cherrypy.config.get('staticFilter.on', False)
            and cherrypy.config.get('sessionFilter.on')):
           self.__loadSession()

    def beforeFinalize(self):
        if (not cherrypy.config.get('staticFilter.on', False)
            and cherrypy.config.get('sessionFilter.on')):
            self.__saveSessions()

    def beforeErrorResponse(self):
        # Still save session data
        if not cherrypy.config.get('staticFilter.on', False) and \
            cherrypy.config.get('sessionFilter.on'):
            self.__saveSessions()
