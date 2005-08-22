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

import time

from sessionerrors import SessionImmutableError

def locker(function):
    def _inner(self, *args, **kwds):
        self._lock.acquire()
        try:
            return function(self, *args, **kwds)
        finally:
            self._lock.release()
    return _inner

import threading 

class SessionDict(dict):

    def __init__(self, sessionData = {}, sessionAttributes = {}):
        self._lock = threading.RLock()
        self.threadCount = 0
        
        dict.__init__(self, sessionData)
        self.__sessionAttributes = sessionAttributes
        
    get=locker(dict.get)
    setdefault=locker(dict.setdefault)

    def __getattr__(self, attr):
        try:
          return self.__sessionAttributes[attr]
        except KeyError:
            return object.__getattribute__(self, attr)
    __getattr__=locker(__getattr__)
    
    # this function we lock the hard way
    # so we don't try to lock the lock
    def __setattr__(self, attr, value):
        if attr == '_lock':
            object.__setattr__(self, attr, value)
            return

        self._lock.acquire()
        
        if attr in ['timeout', 'lastAccess' ]:
            self.__sessionAttributes[attr] = value
        elif attr in ['timestamp', 'key']:
            raise AttributeError('%s is immutable' % attr)
        else:
            object.__setattr__(self, attr, value)

        self._lock.release()
    
    def expired(self):
        now = time.time()
        return (now - self.lastAccess) > self.timeout
    expired = locker(expired)
        
    def __getstate__(self):
        """ remove the lock so we can pickle """
        stateDict = self.__dict__.copy()
        stateDict['threadCount'] = 0
        stateDict.pop('_lock')
        return stateDict
    __getstate__ = locker(__getstate__)

    def __setstate__(self, stateDict):
        """ create a new lock object """
        self.__dict__['_lock'] = threading.RLock()
        self.__dict__.update(stateDict)

    def attributeDict(self):
        return self.__sessionAttributes
