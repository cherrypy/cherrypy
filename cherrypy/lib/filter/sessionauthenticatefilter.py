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

from basefilter import BaseFilter

def defaultLoginScreen(fromPage, login = '', errorMsg = ''):
    return """
    <html><body>
        Message: %s
        <form method="post" action="doLogin">
            Login: <input type="text" name="login" value="%s" size="10"/><br/>
            Password: <input type="password" name="password" size="10"/><br/>
            <input type="hidden" name="fromPage" value="%s"/><br/>
            <input type="submit"/>
        </form>
    </body></html>
    """ % (errorMsg, login, fromPage)

def defaultCheckLoginAndPassword(login, password):
    # Dummy checkLoginAndPassword function
    if login != 'login' or password != 'password':
        return u'Wrong login/password'

class SessionAuthenticateFilter(BaseFilter):
    """
    Filter that adds debug information to the page
    """

    def beforeMain(self):
        global cpg
        from cherrypy import cpg
        if not cpg.config.get('sessionAuthenticateFilter.on', False):
            return
        checkLoginAndPassword = cpg.config.get('sessionAuthenticateFilter.checkLoginAndPassword', defaultCheckLoginAndPassword)
        loginScreen = cpg.config.get('sessionAuthenticateFilter.loginScreen', defaultLoginScreen)
        notLoggedIn = cpg.config.get('sessionAuthenticateFilter.notLoggedIn')
        loadUserByUsername = cpg.config.get('sessionAuthenticateFilter.loadUserByUsername')
        sessionName = cpg.config.get('sessionAuthenticateFilter.sessionName', 'sessionMap')
        sessionKey = cpg.config.get('sessionAuthenticateFilter.sessionKey', 'username')
        sessionMap = getattr(cpg.sessions, sessionName)

        if cpg.request.path.endswith('loginScreen'):
            return
        elif cpg.request.path.endswith('doLogout'):
            sessionMap[sessionKey] = None
            cpg.threadData.user = None
            fromPage = cpg.request.paramMap.get('fromPage')
            if fromPage is None:
                fromPage = '/'
            cpg.response.body = httptools.redirect(fromPage)
        elif cpg.request.path.endswith('doLogin'):
            fromPage = cpg.request.paramMap['fromPage']
            login = cpg.request.paramMap['login']
            password = cpg.request.paramMap['password']
            errorMsg = checkLoginAndPassword(login, password)
            if errorMsg:
                cpg.response.body = loginScreen(fromPage, login = login, errorMsg = errorMsg)
            else:
                sessionMap[sessionKey] = login
                if not fromPage:
                    fromPage = '/'
                cpg.response.body = httptools.redirect(fromPage)
            return

        # Check if user is logged in
        if (not sessionMap.get(sessionKey)) and notLoggedIn:
            # Call notLoggedIn so that applications where anynymous user
            #   is OK can handle it
            notLoggedIn()
        if not sessionMap.get(sessionKey):
            cpg.response.body = loginScreen(cpg.request.browserUrl)
            return

        # Everything is OK: user is logged in
        if loadUserByUsername:
            username = sessionMap[sessionKey]
            cpg.threadData.user = loadUserByUsername(username)
        
