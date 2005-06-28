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

class SessionError(Exception):
    """ Base type for session exceptions. """
    def __init__(self, *args, **kwds):
        Exception.__init__(self, *args, **kwds)

class SessionExpiredError(SessionError):
    """ Possibly raised when the sessions Expire """

class SessionNotFoundError(SessionError):
    """ Possibly raised a browser sends a none with a session idwhen the sessions Expire """

class SessionIncompatibleError(SessionError):
    """ raised if the configured storage type is not compatible with the application """

class SessionImmutableError(SessionError):
    """ immutable exception """
    def __init__(self, keyName):
        self.keyName = keyName

    def __str__(self):
        return "%s is immutable" % self.keyName

class SessionConfigError(SessionError):
    """ finish later """

class SessionBadStorageTypeError(SessionError):
    def __init__(self, storageType):
        self.storageType = self.storageType

    def __str__(self):
        return "Could not find %s storage type." % self.storageType
    
