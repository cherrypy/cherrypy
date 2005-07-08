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

import unittest
import sys
import os

import cherrypy
from cherrypy.test import helper

server_conf = {
               'global' : 
                   {
                    'server.socketHost': helper.HOST,
                    'server.socketPort': helper.PORT,
                    'server.threadPool': 10,
                    'server.logToScreen': False,
                    'server.environment': "production",
                    'sessionFilter.on' : True,
                    'sessionFilter.default.on' : False,
                    'sessionFilter.storagePath' : 'tmpSessionTestData'
                    },
               '/ram'   : { 'sessionFilter.ram.on'   : True, 'sessionFilter.ram.storageType'   : 'ram'   },
               '/file'  : { 'sessionFilter.file.on'  : True, 'sessionFilter.file.storageType'  : 'file'  },
               '/anydb' : { 'sessionFilter.anydb.on' : True, 'sessionFilter.anydb.storageType' : 'anydb' }
              }

cherrypy.config.update(server_conf)

class TestSite:
    
    def __go(self, storageType):
        session = getattr(cherrypy.sessions, storageType)
        count = session.get('count', 0) + 1
        session['count'] = count
        return str(count)


    def ram(self):
        return self.__go('ram')
    ram.exposed = True

    def file(self):
        return self.__go('file')
    file.exposed = True

    def anydb(self):
        return self.__go('anydb')
    anydb.exposed = True

cherrypy.root = TestSite()
cherrypy.config.update(server_conf.copy())

class TutorialTest(unittest.TestCase):

    persistantCookies = {}

    def __testStorageType(self, storageType, startCount = 1, iterations = 0):
        
        #cherrypy.config.update({"sessionFilter.storageType": storageType})
        
        helper.request('/' + storageType)
        self.assertEqual(cherrypy.response.body, str(startCount))
        
        cookie = dict(cherrypy.response.headers)['Set-Cookie']
        
        # this loop will be used to test thread safety
        for n in xrange(startCount+1, startCount + iterations + 1):
            helper.request('/' + storageType, [('Cookie', cookie)])
            self.assertEqual(cherrypy.response.body, str(n))
        
    def testRamSessions(self):
        self.__testStorageType('ram')
    
    def testFileSessions(self):
        self.__testStorageType('file')
    
    def testAnydbSessions(self):
        self.__testStorageType('anydb')

    '''
    def testSqlObjectSession(self):
        self.__testStorageType('sqlobject')
    '''
    
if __name__ == "__main__":
    try:
        os.mkdir('tmpSessionTestData')
        for file in os.listdir('tmpSessionTestData'):
            os.unlink(os.path.join('tmpSessionTestData', file))
    except OSError:
        pass
    cherrypy.server.start(initOnly=True)
    unittest.main()
