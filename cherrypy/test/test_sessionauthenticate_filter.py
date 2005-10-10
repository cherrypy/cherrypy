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

import cherrypy, time, os

class Test:
    def index(self):
        return "Hi, you are logged in"
    index.exposed = True

cherrypy.root = Test()

cherrypy.config.update({
        'server.logToScreen': False,
        'server.environment': 'production',
        'sessionFilter.on': True,
})

cherrypy.config.update({'/':
                        {'sessionAuthenticateFilter.on':True,
                         }
                        })
import helper

class SessionAuthenticateFilterTest(helper.CPWebCase):
    
    def testSessionAuthenticateFilter(self):
        # request a page and check for login form
        self.getPage('/')
        self.assertInBody('<form method="post" action="doLogin">')

        # setup credentials        
        login_body = 'login=login&password=password&fromPage=/'

        # attempt a login
        self.getPage('/doLogin', method='POST', body=login_body)
        self.assertStatus('302 Found')

        # get the page now that we are logged in
        self.getPage('/', self.cookies)
        self.assertBody('Hi, you are logged in')

        # do a logout
        self.getPage('/doLogout', self.cookies)
        self.assertStatus('302 Found')

        # verify we are logged out
        self.getPage('/', self.cookies)
        self.assertInBody('<form method="post" action="doLogin">')
        
        
if __name__ == "__main__":
    helper.testmain()

