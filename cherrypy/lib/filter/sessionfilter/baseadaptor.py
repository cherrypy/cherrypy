"""
Copyright (c) 2004, CherryPy Team (team@cherrypy.org)
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, 
are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice, 
      this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice, 
      this list of conditions and the following disclaimer in the documentation 
      and/or other materials provided with the distribution.
    * Neither the name of the CherryPy Team nor the names of its contributors 
      may be used to endorse or promote products derived from this software 
      without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND 
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED 
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE 
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE 
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL 
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR 
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER 
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, 
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE 
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import random, time, sha, string

import cherrypy

class BaseAdaptor(object):
    """
    This is the class from which all session storage types are derived.
    The functions which need to be redefined are at the end of the file
    """
    
    # by default don't use session caching
    noCache = True
    
    # these are the  functions that need to rewritten 
    def delSession(self, sessionKey):
        """ delete a session from storage """
        raise NotImplementedError('delSession has not been implemented')
    
    def getSession(self, sessionKey):
        """ function to lookup the session """
        raise NotImplementedError('getSession has not been implemented')
    
    def setSession(self, sessionData):
        """ function to save sesion data """
        raise NotImplementedError('setSession has not been implemented')
    
    def cleanUpOldSessions(self):
        """This function cleans up expired sessions"""
        raise NotImplementedError('cleanUpOldSessions has not been implemented')
    
    def newSession(self):
        """ Return a new sessiondict instance """
        raise NotImplementedError('newSession not been implemented')
   
    # it might be usefull to redefine this function
    def generateSessionKey(self):
        """ Function to return a new sessioId """
        try:
            sessionKeyFunc = self.settings.keyGenerator
        except AttributeError:
            sessionKeyFunc = None
        
        if sessionKeyFunc:
            newKey = sessionKeyFunc()
        else:
            newKey = sha.new('%s' % random.random()).hexdigest()
        
        return newKey
    
    def __init__(self, sessionName, sessionPath):
        """
        Create the session caceh and set the session name.  Make if you write
        a custom __init__ function make sure you make a call to 
        BaseAdaptor.__init__(sessioName)
        """
        
        self.__sessionCache = {}
        self.name = sessionName
        
        #set the path
        self.path = sessionPath

        cleanUpDelay = self.getSetting('cleanUpDelay')
        timeMultiple = self.getSetting('timeMultiple')

        self.nextCleanUp = time.time()+cleanUpDelay * timeMultiple

        # find the cookie name
        cookiePrefix = self.getSetting('cookiePrefix')
        
        self.cookieName = '%s_%s' % (cookiePrefix, sessionName)

        try:
            from threading import local
        except ImportError:
            from cherrypy._cpthreadinglocal import local

        # settings dict
        self.settings = None
           
    
    # there should never be a reason to modify the remaining functions, they used 
    # internally by the sessionFilter
    
    def getDefaultAttributes(self):
      return { 
               'timestamp'  : int(time.time()),
               'timeout'    : self.settings.timeout,
               'lastAccess' : int(time.time()),
               'key'        : self.generateSessionKey()
             }
             
    def getSetting(self, settingName, default = None):
        try:
            return getattr(self.settings, settingName)
        except AttributeError:
            missing = object()
            result = cherrypy.config.get('sessionFilter.%s.%s' % (self.name, settingName), missing)
            if result is missing:
                result = cherrypy.config.get('sessionFilter.%s' % settingName, default)

            return result

            
        
    def loadSession(self, sessionKey, autoCreate = True):
        try:
            # look for the session in the cache
            session = self.__sessionCache[sessionKey]
            session.threadCount += 1
        except KeyError:
            # look in the primary storage
            session = self.getSession(sessionKey)
            session.threadCount += 1
            self.__sessionCache[sessionKey] = session
    
        session.cookieName = self.cookieName
        session.lastAccess = time.time()

        setattr(cherrypy.session, self.name, session)
    
    def createSession(self):
        """ returns a session key """
        session = self.newSession()
        self.setSession(session)
        return session.key
    
    def commitCache(self, sessionKey): 
        """ commit a session to persistand storage """
        # this function might require locking
        # but i don't think anything bad could happen ;)
        try:
            session = self.__sessionCache[sessionKey]
            session.threadCount = 0
            self.setSession(session)
        
            cacheTimeout = self.settings.cacheTimeout
            
            if session.threadCount == 0 and (self.noCache or not cacheTimeout):
                del self.__sessionCache[sessionKey]
        except KeyError:
            # i don't think this should happen but it does
            # this is probably the result of two thread calling commitCache
            # but nothing bad should happen
            pass
    
    def cleanUpCache(self):
        """ cleanup all inactive sessions """
        
        cacheTimeout = self.settings.cacheTimeout
        
        # don't waste cycles if we aren't caching inactive sessions
        if cacheTimeout and not self.noCache:
            deleteList = []
            for session in self.__sessionCache.itervalues():
                # make sure the session doesn't have any active threads
                expired = (time.time() - session.lastAccess) < cacheTimeout
                if session.threadCount == 0 and expired:
                    deleteList.append(session)
            for session in deleteList:
                self.commitCache(session.key)
                del self.__sessionCache[session.key]
