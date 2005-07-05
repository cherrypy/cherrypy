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

import cherrypy

# these get copied to the configMap when the filter
# is initilized

_sessionDefaults = {
    'sessionFilter.on' : False,
    'sessionFilter.sessionList' : ['default'],
    'sessionFIlter.storageAdaptors' : {},
    'sessionFilter.default.on': True,
    'sessionFilter.default.timeout': 60,
    'sessionFilter.default.cleanUpDelay': 60,
    'sessionFilter.default.storageType' : 'ram',
    'sessionFilter.default.cookiePrefix': 'CherryPySession',
    'sessionFilter.default.storagePath': '.sessiondata'
}

def _loadDefaults():
    for key, value in _sessionDefaults.iteritems():
        cherrypy.config.configMap['global'].setdefault(key, value)

def retrieve(keyName, sessionName, default = None):
    missing = object()
    value = cherrypy.config.get('sessionFilter.%s.%s'
                                % (sessionName, keyName), missing)
    if value is missing:
        value = cherrypy.config.get('sessionFilter.default.%s'
                                    % keyName, default)
    return value
