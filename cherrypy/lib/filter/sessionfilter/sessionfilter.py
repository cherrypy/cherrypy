
from cherrypy.lib.filter.basefilter import BaseFilter
import cherrypy.cpg

import os.path, time, re

from sessionerrors import SessionNotFoundError 

from ramsession  import RamSession 
from filesession import FileSession
from dbmsession  import DBMSession

_sessionTypes = {
                  'ram'       : RamSession,
                  'file'      : FileSession,
                  'anydb'     : DBMSession
                }

try:
    # the user might not have sqlobject instaled
    from sqlobjectsession  import SQLObjectSession
    _sessionTypes['sqlobject']  = SQLObjectSession
except ImportError:
    pass
    

def _getSessions():
    """ checks the config file for the sessions """
    cpg = cherrypy.cpg
    
    sessions = {}
    
    path = cpg.config.get('sessionFilter.new', returnSection = True )
    paths=os.path.split(path)
    
    sessionNames = cpg.config.getAll('sessionFilter.new')
    for sessionPath in sessionNames:
        sessionName = sessionNames[sessionPath]
        sessionManager = cpg.config.get('%s.sessionManager' % sessionName, None)
        if not sessionManager:
            storageType = cpg.config.get('%s.storageType' % sessionName, 'ram')
            
            #sessionManager = _sessionTypes[storageType](sessionName)
            try:
                sessionManager = _sessionTypes[storageType](sessionName)
            except KeyError:
                storageType = cpg.config.get('%s.customStorageClass' % sessionName)
                if storageType:
                    try:
                        cherrypy._cputil.getSpecialFunction(storageType)
                    except cherrypy.cperror.InternalError:
                        raise SessionBadStorageTypeError(storageType)
                raise
            
            sessionManager.path = sessionPath
            sessionManager.name = sessionName
            sessionManager.lastCleanUp = time.time()
            
            cpg.config.update(
                              {
                                sessionPath : {'%s.sessionManager' % sessionName : sessionManager}
                              }
                             )
        else: # try and clean up
            cleanUpDelay = cpg.config.get('session.cleanUpDelay')
            now = time.time()
            lastCleanUp = sessionManager.lastCleanUp
            if lastCleanUp + cleanUpDelay * 60 <= now:
                sessionManager.cleanUpOldSessions()
          
        sessions[sessionName] = sessionManager
    
    return sessions

class SessionFilter(BaseFilter):
    """
    Input filter - get the sessionId (or generate a new one) and load up the session data
    """
        
    def __initSessions(self):
        cpg = cherrypy.cpg
        sessions = _getSessions()
        sessionKeys = self.getSessionKeys()
        
        for sessionName in sessions:
            sessionManager = sessions[sessionName]
            sessionKey = sessionKeys.get(sessionName, None)
            try:
               sessionManager.loadSession(sessionKey)
            except SessionNotFoundError:
               newKey = sessionManager.createSession()
               sessionManager.loadSession(newKey)
               
               self.setSessionKey(newKey, sessionManager.name) 
                
    def getSessionKeys(self):
        """ 
        Returns the all current sessionkeys as a dict
        """
        cpg = cherrypy.cpg
        
        sessionKeys= {}
        
        sessions = cpg.config.getAll('sessionFilter.new')
        for sessionPath in sessions:
            sessionName = sessions[sessionPath]
            cookieName = cpg.config.get('%s.cookieName' % sessionName, None)
            if not cookieName:
                cookieName = cpg.config.get('session.cookieName') + '|' + re.sub('/','_', sessionPath) + '|' + sessionName
                cpg.config.update({
                                    sessionPath : {'%s.cookieName' % sessionName : cookieName}
                                  })
            try:
                sessionKeys[sessionName] = cpg.request.simpleCookie[cookieName].value
            except:
                sessionKeys[sessionName] = None
        return sessionKeys

    def setSessionKey(self, sessionKey, sessionName):
        """ 
        Sets the session key in a cookie.  Aplications should not call this function,
        but it might be usefull to redefine it.
        """

        cpg = cherrypy.cpg
        
        cookieName = cpg.config.get('%s.cookieName' % sessionName, None)

        cpg.response.simpleCookie[cookieName] = sessionKey
        cpg.response.simpleCookie[cookieName]['version'] = 1

        path = cpg.config.get('%s.sessionManager' % sessionName, returnSection = True)
        cpg.response.simpleCookie[cookieName]['path'] = path

    
    def __saveSessions(self):
        cpg = cherrypy.cpg
        sessions = _getSessions()
        
        for sessionName in sessions:
            sessionManager = sessions[sessionName]
            sessionData = getattr(cpg.sessions, sessionName)
            sessionManager.commitCache(sessionData.key)
    
    def beforeMain(self):
        cpg = cherrypy.cpg
        if cpg.config.get('sessionFilter.on', False) and not cpg.request.isStatic:
           self.__initSessions()

    def beforeFinalize(self):
        cpg = cherrypy.cpg
        if cpg.config.get('sessionFilter.on', False) and not cpg.request.isStatic:
            self.__saveSessions()

    '''
    #this breaks a test case
    def beforeErrorResponse(self):
        # Still save session data
        if cpg.config.get('sessionFilter.on', False) and not cpg.request.isStatic:
            self.__saveSessions()
    '''
