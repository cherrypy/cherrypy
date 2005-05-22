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
from basefilter import BaseInputFilter, BaseOutputFilter

class SetConfig:
    def setConfig(self):
        # We have to dynamically import cpg because Python can't handle
        #   circular module imports :-(
        global cpg
        from cherrypy import cpg
        if cpg.config.get('server.environment') == 'dev':
            # In "dev" environment, log everything by default
            defaultOn = True
        else:
            defaultOn = False

        cpg.threadData.logDebugInfoFilterOn = cpg.config.get('logDebugInfoFilter', defaultOn, cast='bool')
        cpg.threadData.logDebugInfoFilterMimeTypeList = cpg.config.get('logDebugInfoFilter.mimeTypeList', ['text/html'])
        cpg.threadData.logDebugInfoFilterLogBuildTime = cpg.config.get('logDebugInfoFilter.logBuildTime', True, cast='bool')
        cpg.threadData.logDebugInfoFilterLogPageSize = cpg.config.get('logDebugInfoFilter.logPageSize', True, cast='bool')
        cpg.threadData.logDebugInfoFilterLogSessionSize = cpg.config.get('logDebugInfoFilter.logSessionSize', True, cast='bool')
        cpg.threadData.logDebugInfoFilterLogAsComment = cpg.config.get('logDebugInfoFilter.logAsComment', False, cast='bool')

class LogDebugInfoInputFilter(BaseInputFilter, SetConfig):
    """
    Filter that adds debug information to the page
    """

    #def __init__(self, mimeTypeList = ['text/html'], preTag = '<br><br>',
    #        logBuildTime = True, logPageSize = True,
    #        logSessionSize = True, logAsComment = False):
    #    # List of mime-types to which this applies
    #    self.mimeTypeList = mimeTypeList
    #    self.preTag = preTag
    #    self.logBuildTime = logBuildTime
    #    self.logPageSize = logPageSize
    #    self.logSessionSize = logSessionSize
    #    self.logAsComment = logAsComment


    def afterRequestBody(self):
        if not cpg.threadData.logDebugInfoFilterOn:
            return
        cpg.request.startBuilTime = time.time()

class LogDebugInfoOutputFilter(BaseOutputFilter, SetConfig):
    def beforeResponse(self):
        if not cpg.threadData.logDebugInfoFilterOn:
            return
        ct = cpg.response.headerMap.get('Content-Type').split(';')[0]
        if ct in cpg.threadData.logDebugInfoFilterMimeTypeList:
            body = ''.join(cpg.response.body)
            debuginfo = '\n'
            if cpg.threadData.logDebugInfoFilterLogAsComment:
                debuginfo += '<!-- '
            else:
                debuginfo += "<br/><br/>"
            logList = []
            if cpg.threadData.logDebugInfoFilterLogBuildTime:
                logList.append("Build time: %.03fs" % (
                    time.time() - cpg.request.startBuilTime))
            if cpg.threadData.logDebugInfoFilterLogPageSize:
                logList.append("Page size: %.02fKB" % (
                    len(body)/float(1024)))
            if cpg.threadData.logDebugInfoFilterLogSessionSize and \
                    cpg.config.get('session.storageType'):
                # Pickle session data to get its size
                f = StringIO.StringIO()
                pickle.dump(cpg.request.sessionMap, f, 1)
                dumpStr = f.getvalue()
                f.close()
                logList.append("Session data size: %.02fKB" % (
                    len(dumpStr)/float(1024)))

            debuginfo += ', '.join(logList)
            if cpg.threadData.logDebugInfoFilterLogAsComment:
                debuginfo += '-->'

            cpg.response.body = [body, debuginfo]
