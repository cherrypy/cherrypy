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

import basefilter
from cherrypy import cpg, _cphttptools

class VirtualHostFilter(basefilter.BaseInputFilter):
    """
    Filter that changes the ObjectPath based on the Host.
    Useful when running multiple sites within one CP server.
    See CherryPy recipes for the documentation.
    """

    def __init__(self, siteMap, useXForwardedHost = True):
        self.siteMap = siteMap
        self.useXForwardedHost = useXForwardedHost

    def afterRequestHeader(self):
        domain = cpg.request.base.split('//')[1]
        if self.useXForwardedHost:
            domain = cpg.request.headerMap.get( "X-Forwarded-Host", domain)
        prefix = self.siteMap.get(domain)
        if prefix:
            # Re-use "mapPathToObject" function to find the actual
            #   objectPath
            candidate, objectPathList, virtualPathList = \
                    _cphttptools.mapPathToObject(
                        prefix + cpg.request.path
                    )
            cpg.request.objectPath = '/' + '/'.join(objectPathList[1:])
            raise basefilter.InternalRedirect
        
