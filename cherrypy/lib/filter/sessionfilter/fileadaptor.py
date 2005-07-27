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

import cPickle as pickle
import threading
import os.path


from baseadaptor import BaseAdaptor
from sessionerrors import *
from sessiondict import SessionDict


class FileAdaptor(BaseAdaptor):
    
    # is ok to cache filesession data
    noCache = False
    
    def __init__(self, sessionName, sessionPath):
        BaseAdaptor.__init__(self, sessionName, sessionPath)
        self.__fileLock = threading.RLock()

    def newSession(self):
        """ Return a new sessiondict instance """
        newData = self.getDefaultAttributes()
        return SessionDict(sessionAttributes = newData)
   
    # all session writes are blocked 
    def getSession(self, sessionKey):
        if not sessionKey:
            raise SessionNotFoundError
        
        storagePath = self.settings.storagePath

        fileName = '%s-%s' % (self.name, sessionKey)
        filePath = os.path.join(storagePath, fileName)
        
        if os.path.exists(filePath):
            f = open(filePath, "rb")
            self.__fileLock.acquire()
            try:
                sessionData = pickle.load(f)
            finally:
                self.__fileLock.release()
                f.close()
            return sessionData
        else:
            raise SessionNotFoundError
    
    def setSession(self, sessionData):
    
        storagePath = self.settings.storagePath

        fileName = '%s-%s' % (self.name, sessionData.key)
        filePath = os.path.join(storagePath, fileName)

        f = open(filePath,"wb")
        self.__fileLock.acquire()
        pickle.dump(sessionData, f)
        self.__fileLock.release()
        f.close()

    def delSession(self, sessionKey):
        storagePath = self.settings.storagePath
        fileName = '%s-%s' % (self.name, sessionKey)
        filePath = os.path.join(storagePath, fileName)
        
        if os.path.exists(filePath):
            self.__fileLock.acquire()
            os.remove(filePath)
            self.__fileLock.release()
    
    def cleanUpOldSessions(self):
        storagePath = self.settings.storagePath
        sessionFileList = os.listdir(storagePath)
        
        for fileName in sessionFileList:
            try:
                prefix, sessionKey = fileName.split('-')
                if prefix == self.name:
                    session = self.getSession(sessionKey)
                    if session.expired():
                        os.remove(os.path.join(storagePath, fileName))
            except ValueError:
                pass

    def _debugDump(self):
        storagePath = self.settings.storagePath
        sessionFileList = os.listdir(storagePath)
        
        filePrefix = '%s-' % self.name
        dump = {}
        for fileName in sessionFileList:
            try:
                prefix, sessionKey = fileName.split('-')
                if prefix == self.name:
                    dump[sessionKey] = self.getSession(sessionKey)
            except ValueError:
                pass

        return dump

