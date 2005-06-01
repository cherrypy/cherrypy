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

import time, random
from cherrypy import cpg

from aspect import Aspect, STOP, CONTINUE

class CSAuthenticate(Aspect):
    timeoutMessage = "Session timed out"
    wrongLoginPasswordMessage = "Wrong login/password"
    noCookieMessage = "No cookie"
    logoutMessage = "You have been logged out"
    sessionIdCookieName = "CherrySessionId"
    timeout = 60 # in minutes

    def notLoggedIn(self, message):
        return STOP, self.loginScreen(message, cpg.request.browserUrl)

    def _before(self, methodName, method):
        # If the method is not exposed, don't do anything
        if not getattr(method, 'exposed', None):
            return CONTINUE, None

        cpg.request.login = ''
        # If the method is one of these 4, do not try to find out who is logged in
        if methodName in ["loginScreen", "logoutScreen", "doLogin", "doLogout", "notLoggedIn"]:
            return CONTINUE, None

        # Check if a user is logged in:
        #   - If they are, set request.login with the right value
        #   - If not, return the login screen
        if not cpg.request.simpleCookie.has_key(self.sessionIdCookieName):
            # return STOP, self.loginScreen(self.noCookieMessage, cpg.request.browserUrl)
            return self.notLoggedIn(self.noCookieMessage)
        sessionId = cpg.request.simpleCookie[self.sessionIdCookieName].value
        now=time.time()

        # Check that session exists and hasn't timed out
        timeout=0
        if not cpg.request.sessionMap.has_key(sessionId):
            # return STOP, self.loginScreen(self.noCookieMessage, cpg.request.browserUrl)
            return self.notLoggedIn(self.noCookieMessage)
        else:
            login, expire = cpg.request.sessionMap[sessionId]
            if expire < now: timeout=1
            else:
                expire = now + self.timeout*60
                cpg.request.sessionMap[sessionId] = login, expire

        if timeout:
            # return STOP, self.loginScreen(self.timeoutMessage, cpg.request.browserUrl)
            return self.notLoggedIn(self.timeoutMessage)

        cpg.request.login = login
        return CONTINUE, None

    def checkLoginAndPassword(self, login, password):
        if (login,password) == ('login','password'): return ''
        return 'Wrong login/password'

    def generateSessionId(self, sessionIdList):
        choice="0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        while 1:
            sessionId=""
            for dummy in range(20): sessionId += random.choice(choice)
            if sessionId not in sessionIdList: return sessionId

    def doLogin(self, login, password, fromPage):
        # Check that login/password match
        errorMsg = self.checkLoginAndPassword(login, password)
        if errorMsg:
            cpg.request.login = ''
            return self.loginScreen(errorMsg, fromPage, login)
        cpg.request.login = login
        # Set session
        newSessionId = self.generateSessionId(cpg.request.sessionMap.keys())
        cpg.request.sessionMap[newSessionId] = login, time.time()+self.timeout*60
        
        cpg.response.simpleCookie[self.sessionIdCookieName] = newSessionId
        cpg.response.simpleCookie[self.sessionIdCookieName]['path'] = '/'
        cpg.response.simpleCookie[self.sessionIdCookieName]['max-age'] = 31536000
        cpg.response.simpleCookie[self.sessionIdCookieName]['version'] = 1
        cpg.response.status = "302 Found"
        cpg.response.headerMap['Location'] = fromPage
        return ""
    doLogin.exposed = True

    def doLogout(self):
        try:
            sessionId = request.simpleCookie[self.sessionIdCookieName].value
            del request.sessionMap[sessionId]
        except: pass
        
        cpg.response.simpleCookie[self.sessionIdCookieName] = ""
        cpg.response.simpleCookie[self.sessionIdCookieName]['path'] = '/'
        cpg.response.simpleCookie[self.sessionIdCookieName]['max-age'] = 0
        cpg.response.simpleCookie[self.sessionIdCookieName]['version'] = 1
        cpg.request.login = ''
        cpg.response.status = "302 Found"
        cpg.response.headerMap['Location'] = 'logoutScreen'
        return ""
    doLogout.exposed = True

    def logoutScreen(self):
        return self.loginScreen(self.logoutMessage, '/index') # TBC
    logoutScreen.exposed = True

    def loginScreen(self, message, fromPage, login=''):
        return """
        <html><body>
            Message: %s
            <form method="post" action="doLogin">
                Login: <input type=text name=login value="%s" size=10/><br/>
                Password: <input type=password name=password size=10/><br/>
                <input type=hidden name=fromPage value="%s"/><br/>
                <input type=submit/>
            </form>
        </body></html>
        """ % (message, login, fromPage)
    loginScreen.exposed = True
