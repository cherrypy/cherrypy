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

from basesession import BaseSession
import cherrypy.cpg
import cPickle as pickle

import os.path

from sessionerrors import *
import sessionconfig

import threading
from simplesessiondict import SimpleSessionDict

class FileSession(BaseSession):
  
    def __init__(self, sessionName):
        BaseSession.__init__(self, sessionName)
        self.__fileLock = threading.RLock()

    def __storageDir(self):
        cpg = cherrypy.cpg
        storageDir = sessionconfig.retrieve('storageFileDir', self.sessionName, '.sessionFiles')
        return storageDir
    
    def newSession(self):
        """ Return a new sessiondict instance """
        newData = self.getDefaultAttributes()
        return SimpleSessionDict(newData)
   
    # all session writes are blocked 
    def getSession(self, sessionKey):
        sessionStorageFileDir = self.__storageDir()
        print sessionStorageFileDir, sessionKey
        fname = os.path.join(sessionStorageFileDir, sessionKey)
        if os.path.exists(fname):
            f = open(fname, "rb")
            self.__fileLock.acquire()
            sessionData = pickle.load(f)
            self.__fileLock.release()
            f.close()
            return sessionData
        else:
            raise SessionNotFoundError
    
    def setSession(self, sessionData):
        sessionStorageFileDir = self.__storageDir()
    
        fname=os.path.join(sessionStorageFileDir, sessionData.key)
        f = open(fname,"wb")
        self.__fileLock.acquire()
        pickle.dump(sessionData, f)
        self.__fileLock.acquire()
        f.close()

    def delSession(self, sessionKey):
        sessionStorageFileDir = self.__storageDir()
    
    def cleanUpOldSessions(self):
        sessionStorageFileDir = self.__storageDir()
        sessionFileList = os.listdir(sessionStorageFileDir)

        for sessionKey in sessionFileList:
            session = self.getSession(sessionKey)
            if session.expired():
                try:
                    os.remove(os.path.join(sessionStorageFileDir, sessionKey))
                except:
                    """ the session was probably removed already """
