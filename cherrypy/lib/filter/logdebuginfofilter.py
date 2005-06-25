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

try:
    import cPickle as pickle
except ImportError:
    import pickle

from basefilter import BaseFilter


class LogDebugInfoFilter(BaseFilter):
    """Filter that adds debug information to the page"""
    
    def onStartResource(self):
        # We have to dynamically import cherrypy because Python can't handle
        #   circular module imports :-(
        global cherrypy
        import cherrypy
    
    def beforeMain(self):
        cherrypy.request.startBuilTime = time.time()
    
    def beforeFinalize(self):
        if cherrypy.config.get('server.environment') == 'development':
            # In "dev" environment, log everything by default
            defaultOn = True
        else:
            defaultOn = False
        
        if not cherrypy.config.get('logDebugInfoFilter.on', defaultOn):
            return
        
        mimelist = cherrypy.config.get('logDebugInfoFilter.mimeTypeList', ['text/html'])
        ct = cherrypy.response.headerMap.get('Content-Type').split(';')[0]
        if ct in mimelist:
            body = ''.join(cherrypy.response.body)
            debuginfo = '\n'
            
            logAsComment = cherrypy.config.get('logDebugInfoFilter.logAsComment', False)
            if logAsComment:
                debuginfo += '<!-- '
            else:
                debuginfo += "<br/><br/>"
            logList = []
            
            if cherrypy.config.get('logDebugInfoFilter.logBuildTime', True):
                logList.append("Build time: %.03fs" % (
                    time.time() - cherrypy.request.startBuilTime))
            
            if cherrypy.config.get('logDebugInfoFilter.logPageSize', True):
                logList.append("Page size: %.02fKB" % (
                    len(body)/float(1024)))
            ''' 
            # this is not compatible with the session filter
            if (cherrypy.config.get('logDebugInfoFilter.logSessionSize', True)
                and cherrypy.config.get('session.storageType')):
                # Pickle session data to get its size
                try:
                    dumpStr = pickle.dumps(cherrypy.request.sessionMap, 1)
                    logList.append("Session data size: %.02fKB" %
                                   (len(dumpStr) / float(1024)))
                except:
                    logList.append("Session data size: Unable to pickle session")
            '''
            
            debuginfo += ', '.join(logList)
            if logAsComment:
                debuginfo += '-->'
            
            cherrypy.response.body = [body, debuginfo]
