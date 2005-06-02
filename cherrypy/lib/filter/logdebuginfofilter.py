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

import time, StringIO, pickle
from basefilter import BaseFilter

class LogDebugInfoFilter(BaseFilter):
    """Filter that adds debug information to the page"""
    
    def beforeMain(self):
        # We have to dynamically import cpg because Python can't handle
        #   circular module imports :-(
        global cpg
        from cherrypy import cpg
        cpg.request.startBuilTime = time.time()
    
    def beforeFinalize(self):
        if cpg.config.get('server.environment') == 'dev':
            # In "dev" environment, log everything by default
            defaultOn = True
        else:
            defaultOn = False
        
        if not cpg.config.get('logDebugInfoFilter.on', defaultOn):
            return
        
        mimelist = cpg.config.get('logDebugInfoFilter.mimeTypeList', ['text/html'])
        ct = cpg.response.headerMap.get('Content-Type').split(';')[0]
        if ct in mimelist:
            body = ''.join(cpg.response.body)
            debuginfo = '\n'
            
            logAsComment = cpg.config.get('logDebugInfoFilter.logAsComment', False)
            if logAsComment:
                debuginfo += '<!-- '
            else:
                debuginfo += "<br/><br/>"
            logList = []
            
            if cpg.config.get('logDebugInfoFilter.logBuildTime', True):
                logList.append("Build time: %.03fs" % (
                    time.time() - cpg.request.startBuilTime))
            
            if cpg.config.get('logDebugInfoFilter.logPageSize', True):
                logList.append("Page size: %.02fKB" % (
                    len(body)/float(1024)))
            
            if (cpg.config.get('logDebugInfoFilter.logSessionSize', True)
                and cpg.config.get('session.storageType')):
                # Pickle session data to get its size
                try:
                    f = StringIO.StringIO()
                    pickle.dump(cpg.request.sessionMap, f, 1)
                    dumpStr = f.getvalue()
                    f.close()
                    logList.append("Session data size: %.02fKB" %
                                   (len(dumpStr) / float(1024)))
                except:
                    logList.append("Session data size: Unable to pickle session")
            
            debuginfo += ', '.join(logList)
            if logAsComment:
                debuginfo += '-->'
            
            cpg.response.body = [body, debuginfo]
