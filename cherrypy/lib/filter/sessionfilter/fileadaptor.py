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
import mrow
import cherrypy

from baseadaptor import BaseAdaptor
from sessionerrors import *
from sessiondict import SessionDict

class FileAdaptor(BaseAdaptor):
    
    # is ok to cache filesession data
    noCache = False
    
    def __init__(self):
        BaseAdaptor.__init__(self)
        self.__fileLock = mrow.MROWLock() 

    # all session writes are blocked 
    def _getSessionDict(self, sessionKey):
        if not sessionKey:
            raise SessionNotFoundError()
        
        storagePath = cherrypy.config.get('sessionFilter.storagePath')

        fileName = 'sessionFile-' + sessionKey
        filePath = os.path.join(storagePath, fileName)
        
        if os.path.exists(filePath):
            f = open(filePath, "rb")
            self.__fileLock.lock_read()
            try:
                sessionData = pickle.load(f)
            finally:
                self.__fileLock.unlock_read()
                f.close()
            return sessionData
        else:
            raise SessionNotFoundError()
    
    def saveSessionDict(self, sessionData):
    
        storagePath = cherrypy.config.get('sessionFilter.storagePath')

        fileName = 'sessionFile-' + sessionData.key
        filePath = os.path.join(storagePath, fileName)

        self.__fileLock.lock_write()
        try:
            f = open(filePath,"wb")
            pickle.dump(sessionData, f)
            f.close()
        finally:
            self.__fileLock.unlock_write()

    def _cleanUpOldSessions(self):
        self.__fileLock.lock_read()
        try:
            storagePath = cherrypy.config.get('sessionFilter.storagePath')
            sessionFileList = os.listdir(storagePath)
            
            for fileName in sessionFileList:
                try:
                    prefix, sessionKey = fileName.split('-')
                    if prefix == 'sessionFile':
                        session = self._getSessionDict(sessionKey)
                        if session.expired():
                            os.remove(os.path.join(storagePath, fileName))
                except ValueError:
                    pass
        finally:
            self.__fileLock.unlock_read()
    
    def _sessionCount(self):
        self.__fileLock.lock_read()
        try:
            storagePath = cherrypy.config.get('sessionFilter.storagePath')
            sessionFileList = os.listdir(storagePath)
        
            count = 0
            for fileName in sessionFileList:
                if fileName.startswith('sessionFile-'):
                    count += 1
        
            return count
        finally:
            self.__fileLock.lock_read()
        
    
