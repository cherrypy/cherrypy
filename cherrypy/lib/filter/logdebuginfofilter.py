"""
Copyright (c) 2004, CherryPy Team (team@cherrypy.org)
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
    * Neither the name of the CherryPy Team nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import time, StringIO, pickle
from basefilter import BaseInputFilter, BaseOutputFilter
from cherrypy import cpg
from itertools import chain

class LogDebugInfoStartFilter(BaseInputFilter, BaseOutputFilter):
    """
    Filter that adds debug information to the page
    """

    def __init__(self, mimeTypeList = ['text/html'], preTag = '<br><br>',
            logBuildTime = True, logPageSize = True,
            logSessionSize = True, logAsComment = False):
        # List of mime-types to which this applies
        self.mimeTypeList = mimeTypeList
        self.preTag = preTag
        self.logBuildTime = logBuildTime
        self.logPageSize = logPageSize
        self.logSessionSize = logSessionSize
        self.logAsComment = logAsComment

    def afterRequestBody(self):
        cpg.request.startBuilTime = time.time()

    def beforeResponse(self):
        ct = cpg.response.headerMap.get('Content-Type')
        if (ct in self.mimeTypeList):
            debuginfo = '\n'
            if self.logAsComment:
                debuginfo += '<!-- '
            else:
                debuginfo += self.preTag
            logList = []
            if self.logBuildTime:
                logList.append("Build time: %.03fs" % (
                    time.time() - cpg.request.startBuilTime))
            if self.logPageSize:
                logList.append("Page size: %.02fKB" % (
                    len(cpg.response.body)/float(1024)))
            if self.logSessionSize and cpg.configOption.sessionStorageType:
                # Pickle session data to get its size
                f = StringIO.StringIO()
                pickle.dump(cpg.request.sessionMap, f, 1)
                dumpStr = f.getvalue()
                f.close()
                logList.append("Session data size: %.02fKB" % (
                    len(dumpStr)/float(1024)))

            debuginfo += ', '.join(logList)
            if self.logAsComment:
                debuginfo += '-->'

            cpg.response.body = chain(cpg.response.body, [debuginfo])
