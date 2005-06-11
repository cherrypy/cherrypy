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

import cherrypy.cpg

import cherrypy._cputil, cherrypy.cperror
import random, time, sha, string

from sessiondict import SimpleSessionDict

import sessionconfig

class BaseSession(object):
    """
    This is the class from which all session storage types are derived.
    """

    # configname is the string storageType value used by the 
    # configuration file
    configName = 'BaseSession'
    
    """
    autoKeys is used to tell the server if the session storage class
    can automaticly determine all of the key names.  This would be 
    true if you are using a relational database and false if you are 
    using python dictionaries.

    If autoKeys is false the key names must be provided at runtime.
    If it is true any key names provied at runtime are ignored.
    """
    autoKeys   = True
    

    def __init__(self, sessionName):
        self.__sessionCache = {}
        self.defaultValues = {}
        self.sessionName = sessionName
        """
        This is where the you initialize your session storage class.
        sessionOptions is a direct mapping of the configuration
        options.
        
        The keys 'host', 'user', 'password', and 'database',
        must be used by classes that need to connect to remote
        databases.  'tableName' will contain the table name (duh!).

        The keyw 'dataKeys' will map to a list of the variable names you wish
        to store in your session object.  If autoKeys is true you will use it
        to set to create sessionMap instances.
        """
    
    def getDefaultAttributes(self):
      return { 
               'timestamp'  : int(time.time()),
               'timeout'    : sessionconfig.retrieve('timeout', self.sessionName) * 60,
               'lastAccess' : int(time.time()),
               'key' : self.generateSessionKey()
             }
       
    def newSession(self):
        """ Return a new sessionMap instance """
        # this needs to check the config file for default values
        newData = self.getDefaultAttributes()
        newData.update(self.defaultValues)
        return SimpleSessionDict(newData)

    def generateSessionKey(self):
        """ Function to return a new sessioId """
        sessionKeyFunc = sessionconfig.retrieve('keyGenerator', self.sessionName, None)
        
        if sessionKeyFunc:
            newKey = cherrypy._cputil.getSpecialAttribute(sessionKeyFunc)()
        else:
            s = ''
            for i in range(50):
                s += random.choice(string.letters+string.digits)
            s += '%s'%time.time()
            newKey = sha.sha(s).hexdigest()
        
        return newKey

    def loadSession(self, sessionKey, autoCreate = True):
        cpg = cherrypy.cpg
        
        try:
            # look for the session in the cache
            session = self.__sessionCache[sessionKey]
            session.threadCount += 1
        except KeyError:
            # look in the primary storage
            session = self.getSession(sessionKey)
            session.threadCount += 1
            self.__sessionCache[sessionKey] = session
        
        if self.sessionName == 'sessionMap':
            # raise a warning perhaps
            setattr(cpg.request, self.sessionName, session)
        setattr(cpg.sessions, self.sessionName, session)

    def createSession(self):
        """ returns a session key """
        session = self.newSession()
        self.setSession(session)
        return session.key

    def commitCache(self, sessionKey): 
        
        session = self.__sessionCache[sessionKey]
        session.threadCount = 0
        self.setSession(session)
        
        cacheTimeout = sessionconfig.retrieve('%s.cacheTimeout' % self.sessionName, None)
        if not cacheTimeout:
            cacheTimeout = sessionconfig.retrieve('sessionFilter.cacheTimeout', None)
        
        if session.threadCount == 0 and not cacheTimeout:
            del self.__sessionCache[sessionKey]
        """ commit a session to persistand storage """
    
    def cleanUpCache(self):
        """ cleanup all inactive sessions """
        
        cacheTimeout = sessionconfig.retrieve('%s.cacheTimeout' % self.sessionName, None)
        
        # don't waste cycles if we aren't caching inactive sessions
        if cacheTimeout:
            for session in self.__sessionCache.itervalues():
                # make sure the session doesn't have any active threads
                expired = time.time() < (session.lastAccess + cacheTimeout)
                if session.threadCount == 0 and expired:
                    del self.__sessionCache[session.key]
    
    def dropSession(self, sessionKey):
        self.delSession()
        """ delete a session from storage """

    def cleanUpOldSessions(self):
        """This function cleans up expired sessions"""

