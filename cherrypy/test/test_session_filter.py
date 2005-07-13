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

testThreadCount = 3

import unittest
import sys
import os

import cherrypy
from cherrypy.test import helper

localDir = os.path.dirname(__file__)
curpath = os.path.normpath(os.path.join(os.getcwd(), localDir))
tmpFolder = os.path.join(curpath, 'tmpSessionTestData')

server_conf = {
               'global' : 
                   {
                    'server.socketHost': helper.HOST,
                    'server.socketPort': helper.PORT,
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
               '/ram'   : { 'sessionFilter.ram.on'   : True, 'sessionFilter.ram.storageType'   : 'ram'   },
               '/file'  : { 'sessionFilter.file.on'  : True, 'sessionFilter.file.storageType'  : 'file'  },
               '/anydb' : { 'sessionFilter.anydb.on' : True, 'sessionFilter.anydb.storageType' : 'anydb' }
              }

cherrypy.config.update(server_conf)

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
        
import threading

cherrypy.root = TestSite()
cherrypy.config.update(server_conf.copy())
import time




class sessionTest:
    
    def __testSession(self):

        helper.request(self.sessionPath)
        if cherrypy.response.body != '1':
            raise cherrypy.response.body
            raise "Error creating a new session.\n"
        
        cookie = dict(cherrypy.response.headers)['Set-Cookie']

        # this loop will be used to test thread safety
        for n in xrange(0, self.iterations):
            if self.persistant:
                cherrypy.server.stop()
                cherrypy.server.start(initOnly = True)
            helper.request(self.sessionPath, [('Cookie', cookie)])
            if cherrypy.response.body != str(n+2):
                raise "Error using session data."
        
    def __testCleanUp(self, sessionCount = 1):
        SessionFilter = cherrypy._cputil._cpDefaultFilterInstances['SessionFilter']
        
        #  create several new sessions
        for n in xrange(sessionCount):
            helper.request(self.sessionPath)

        sessionManagers = SessionFilter.sessionManagers

        time.sleep(1)
        # this should trigger a clean up
        helper.request(self.sessionPath)
        SessionCount = len(sessionManagers[self.sessionName]._debugDump())
        sessionManagers[self.sessionName].cleanUpOldSessions()
        if SessionCount != 1:
            raise 'clean up failed %s != 1' % SessionCount
#        self.assertEqual(1, SessionCount)
    
    def __testThreadSafety(self):
        for z in range(3):
            threading.Thread(target = self.__testSession).start()
            
    def __init__(self, sessionName, sessionPath, storageType, persistant):
        self.cookies = []

        self.iterations = 2
        
        self.sessionName = sessionName
        self.sessionPath = sessionPath
        self.storageType = storageType
        self.persistant  = persistant
        
    
    def __call__(self):
        self.__testSession()
        self.persistant = False
        self.__testCleanUp()


testSessions = {
  'default' : ('/', 'ram', False),
  'ram'     : ('/ram', 'ram', False),
  'file'    : ('/file', 'file', True),
  'anydb'   : ('/anydb', 'anydb', True)
}
class SessionFilterTest(unittest.TestCase):

    def __testCacheCleanUp(self, storageType):
        pass
    
    '''

    def testSqlObjectSession(self):
        self.__testSession('sqlobject')
    '''

for key, values in testSessions.iteritems():
    if key == 'default' or 1: 
        st = sessionTest(key, values[0], values[1], values[2])
        setattr(SessionFilterTest, 'test%s' % key, st)
    

if __name__ == "__main__":
    try:
        os.mkdir(tmpFolder)
    except OSError:
        pass
   
    cherrypy.server.start(initOnly = True)
    unittest.main()
