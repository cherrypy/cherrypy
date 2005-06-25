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
from cherrypy.lib.filter.sessionfilter.simplesessiondict import SimpleSessionDict
from cherrypy.lib.filter.sessionfilter import sessionconfig


class BaseSession(object):
    """
    This is the class from which all session storage types are derived.
    The functions which need to be redefined are at the end of the file
    """
    
    # by default don't use session caching
    noCache = True
    
    # these are the  functions that need to rewritten 
    def delSession(self, sessionKey):
        """ delete a session from storage """
        pass
    
    def getSession(self, sessionKey):
        """ function to lookup the session """
        pass
    
    def setSession(self, sessionData):
        """ function to save sesion data """
        pass
    
    def cleanUpOldSessions(self):
        """This function cleans up expired sessions"""
        pass
    
    def newSession(self):
        """ Return a new sessiondict instance """
        pass
    
    # it might be usefull to redefine this function
    def generateSessionKey(self):
        """ Function to return a new sessioId """
        sessionKeyFunc = sessionconfig.retrieve('keyGenerator', self.sessionName, None)
        
        if sessionKeyFunc:
            from cherrypy import _cputil
            newKey = _cputil.getSpecialAttribute(sessionKeyFunc)()
        else:
            newKey = sha.new('%s%s' % (time.time(), random.random())).hexdigest()
        
        return newKey
    
    def __init__(self, sessionName):
        """
        Create the session caceh and set the session name.  Make if you write
        a custom __init__ function make sure you make a call to 
        BaseSession.__init__(sessioName)
        """
        
        self.__sessionCache = {}
        self.sessionName = sessionName
    
    
    # there should never be a reason to modify the remaining functions, they used 
    # internally by the sessionFilter
    
    def getDefaultAttributes(self):
      return { 
               'timestamp'  : int(time.time()),
               'timeout'    : sessionconfig.retrieve('timeout', self.sessionName) * 60,
               'lastAccess' : int(time.time()),
               'key' : self.generateSessionKey()
             }
       
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
        
        setattr(cherrypy.sessions, self.sessionName, session)
    
    def createSession(self):
        """ returns a session key """
        session = self.newSession()
        self.setSession(session)
        return session.key
    
    def commitCache(self, sessionKey): 
        """ commit a session to persistand storage """
        
        session = self.__sessionCache[sessionKey]
        session.threadCount = 0
        self.setSession(session)
        
        cacheTimeout = sessionconfig.retrieve('cacheTimeout',  self.sessionName, None)
        
        if session.threadCount == 0 and (self.noCache or not cacheTimeout):
            del self.__sessionCache[sessionKey]
    
    def cleanUpCache(self):
        """ cleanup all inactive sessions """
        
        cacheTimeout = sessionconfig.retrieve('cacheTimeout',  self.sessionName, None)
        
        # don't waste cycles if we aren't caching inactive sessions
        if cacheTimeout and not self.noCache:
            for session in self.__sessionCache.itervalues():
                # make sure the session doesn't have any active threads
                expired = time.time() < (session.lastAccess + cacheTimeout * 60)
                if session.threadCount == 0 and expired:
                    del self.__sessionCache[session.key]
