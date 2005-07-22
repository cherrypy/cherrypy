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

import threading
import time
import unittest
import sys
import os

import cherrypy
from cherrypy.test import helper

localDir = os.path.dirname(__file__)
curpath = os.path.normpath(os.path.join(os.getcwd(), localDir))
tmpFolder = os.path.join(curpath, 'tmpSessionTestData')

server_conf = {
               'global':
                   {
                    'server.socketHost': '127.0.0.1',
                    'server.socketPort': 8000,
                    'server.threadPool': 5,
                    'server.logToScreen': False,
                    'server.environment': "production",
                    'sessionFilter.on' : True,
                    'sessionFilter.cacheTimeout' : 60,
                    'sessionFilter.storagePath' : tmpFolder,
                    'sessionFilter.default.on' : True,
                    'sessionFilter.timeMultiple' : 1,
                    'sessionFilter.cleanUpDelay' : 1,
                    'sessionFilter.timeout' : 1,
                    'testMode' : True
                    },
               '/ram':
                   {'sessionFilter.ram.on': True,
                    'sessionFilter.ram.storageType': 'ram'},
               '/file':
                   {'sessionFilter.file.on': True,
                    'sessionFilter.file.storageType': 'file'},
               '/anydb':
                   {'sessionFilter.anydb.on': True,
                    'sessionFilter.anydb.storageType': 'anydb'},
              }


class TestSite:
    
    def __go(self, storageType):
        session = getattr(cherrypy.session, storageType)
        count = session.setdefault('count', 1)
        session['count'] = count + 1
        return str(count)
    
    def index(self):
        count = cherrypy.session.setdefault('count', 1)
        cherrypy.session['count'] = count + 1
        return str(count)
    index.exposed = True
    
    def default(self, sessionName):
        return self.__go(sessionName)
    default.exposed = True

cherrypy.root = TestSite()
cherrypy.config.update(server_conf.copy())


class SessionFilterTest(helper.CPWebCase):
    
##    def test_default(self):
##        self.sessionName = "default"
##        self.sessionPath = "/"
##        self.storageType = "ram"
##        self.persistant  = False
##        self.doSession()
##        self.persistant = False
##        self.doCleanUp()
##        self.doThreadSafety()
    
    def test_ram(self):
        self.sessionName = "ram"
        self.sessionPath = "/ram"
        self.storageType = "ram"
        self.persistant  = False
        self.doSession()
        self.persistant = False
        self.doCleanUp()
        self.doSession(threaded = True)
        self.doThreadSafety()
    
    def test_file(self):
        self.sessionName = "file"
        self.sessionPath = "/file"
        self.storageType = "file"
        self.persistant  = True
        self.doSession()
        self.persistant = False
        self.doCleanUp()
        self.doSession(threaded = True)
        self.doThreadSafety()
    
    def test_anydb(self):
        self.sessionName = "anydb"
        self.sessionPath = "/anydb"
        self.storageType = "anydb"
        self.persistant  = True
        self.doSession()
        self.persistant = False
        self.doCleanUp()
        self.doSession(threaded = True)
        self.doThreadSafety()
    
    threadTesting = False
    
    def doSession(self, threaded = False):
        self.getPage(self.sessionPath)
        self.assertBody('1')
        
        h = []
        for k, v in cherrypy.response.headers:
            if k == 'Set-Cookie':
                h.append(('Cookie', v))
        getPageArgs = (self.sessionPath, h)
        
        # this loop will be used to test thread safety
        for n in xrange(2):
            if self.persistant and not self.threadTesting:
                cherrypy.server.stop()
                cherrypy.server.start(initOnly = True)
            if not threaded:
                self.getPage(*getPageArgs)
            else:
                import webtest
                webtest.ignore_all = True
                thread = threading.Thread(target = self.getPage, args = getPageArgs)
                thread.start()
                while thread.isAlive():
                    pass
                webtest.ignore_all = False
            
        self.assertBody(str(3))
    
    def doThreadSafety(self):
        return
        self.threadTesting = True
        for n in xrange(13):
            thread = threading.Thread(target=self.doSession)
            thread.start()
        print cherrypy.response.body
        self.threadTesting = False
        
    def doCleanUp(self):
        SessionFilter = cherrypy._cputil._cpDefaultFilterInstances['SessionFilter']
        
        #  create several new sessions
        for n in xrange(5):
            self.getPage(self.sessionPath)
        
        sessionManagers = SessionFilter.sessionManagers
        
        time.sleep(1)
        # this should trigger a clean up
        self.getPage(self.sessionPath)
        
        SessionCount = len(sessionManagers[self.sessionName]._debugDump())
        sessionManagers[self.sessionName].cleanUpOldSessions()
        self.assertEqual(SessionCount, 1)


if __name__ == "__main__":
    try:
        os.mkdir(tmpFolder)
    except OSError:
        pass
    
    helper.testmain()
