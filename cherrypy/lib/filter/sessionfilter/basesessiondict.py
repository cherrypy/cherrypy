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
import time

from sessionerrors import SessionImmutableError

def locker(function):
    def _inner(self, *args, **kwds):
        self._lock.acquire()
        result = function(self, *args, **kwds)
        self._lock.release()
        return result
    return _inner

import threading 

# this is a dictionary like class that will be exposed to the application
# this class is used by 
class BaseSessionDict(object):
    """
    cpg.request.sessionMap is a SessionDict instance.

    SessionDict isntances alwasy contain the following attributes.
    
    'sessionKey' : A unique session identifier
    
    'timeout'    : The number of seconds of inactivity allowed before destroying the session

    'timestamp'  : The time the session was created (seconds since the Epoch or time.time() )
    'lastAccess' : The time the last session was accessed (seconds since the Epoch or time.time() )

    sessionKey and createdAt are immutable and a SessionImmutableError will be raised if you
    try to set one
    """


    def __init__(self):
        pass
    
    def __eq__(self, sessionDict):
        pass 
        
    def get(self, key, default = None):
        try:
            return self.__getitem__(key)
        except KeyError:
            return default
        
    def __getitem__(self, key):
        pass 
     
    def __setitem__(self, key, value):
        pass 

    def __getattr__(self, attr):
        pass 
    
    def __setattr__(self, attr, value):
        pass 
    
    def expired(self):
        now = time.time()
        return (now - self.lastAccess) < self.timeout
    
    # additional functions
    '''
    def __getstate__(self):
        pass

    def __setstate__(self, stateDict):
        pass
    '''

