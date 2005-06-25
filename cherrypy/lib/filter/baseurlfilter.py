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

from basefilter import BaseFilter


class BaseUrlFilter(BaseFilter):
    """Filter that changes the base URL.
    
    Useful when running a CP server behind Apache.
    """
    
    def beforeRequestBody(self):
        import cherrypy
        
        if not cherrypy.config.get('baseUrlFilter.on', False):
            return
        
        req = cherrypy.request
        newBaseUrl = cherrypy.config.get('baseUrlFilter.baseUrl', 'http://localhost')
        if cherrypy.config.get('baseUrlFilter.useXForwardedHost', True):
            newBaseUrl = req.headerMap.get("X-Forwarded-Host", newBaseUrl)
        
        if newBaseUrl.find("://") == -1:
            # add http:// or https:// if needed
            newBaseUrl = req.base[:req.base.find("://") + 3] + newBaseUrl
        
        req.browserUrl = req.browserUrl.replace(req.base, newBaseUrl)
        req.base = newBaseUrl
