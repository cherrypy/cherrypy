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

import shelve

import cherrypy
from basesession import BaseSession
from sessionerrors import *
from simplesessiondict import SimpleSessionDict

import sessionconfig

import os.path


class DBMSession(BaseSession):
   
    # it is ok to cache the session data
    noCache = False
    
    def __init__(self, sessionName, sessionPath):
        BaseSession.__init__(self, sessionName, sessionPath)
        
        # we must make sure the db file is unique
        dbFile = cherrypy.config.get('sessionFilter.%s.dbFile', None)
        if not dbFile:
            defaultFile = '%s.db' % sessionName
            storagePath = sessionconfig.retrieve('storagePath', sessionName)
            dbFile = os.path.join(storagePath, defaultFile)
        self.__data = shelve.open(dbFile, 'c')
    
    def newSession(self):
        """ Return a new sessiondict instance """
        newData = self.getDefaultAttributes()
        return SimpleSessionDict(newData)

    def getSession(self, sessionKey):
        try:
            return self.__data[sessionKey]
        except KeyError:
            raise SessionNotFoundError
    
    def setSession(self, sessionData):
        self.__data[sessionData.key] = sessionData

    def delSession(self, sessionKey):
        try:
            del self.__data[sessionKey]
        except KeyError:
            raise SessionNotFoundError
    
    def cleanUpOldSessions(self):
        deleteList = []
        for sessionKey in self.__data:
            session = self.__data[sessionKey]
            if session.expired():
                deleteList.append(sessionKey)
        for key in deleteList:
            self.delSession(sessionKey)
