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

def loginScreen(fromPage, login = '', errorMsg = ''):
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


class SessionAuthenticateFilter(BaseFilter):
    """
    Filter that adds debug information to the page
    """

    def __init__(self, checkLoginAndPassword, loginScreen = loginScreen,
            notLoggedIn = None, loadUserByUsername = None):
        global cpg, httptools
        # We have to dynamically import cpg because Python can't handle
        #   circular module imports :-(
        from cherrypy import cpg
        from cherrypy.lib import httptools
        self.checkLoginAndPassword = checkLoginAndPassword
        self.loginScreen = loginScreen
        self.notLoggedIn = notLoggedIn
        self.loadUserByUsername = loadUserByUsername

    def beforeMain(self):
        if cpg.request.path.endswith('loginScreen'):
            return
        elif cpg.request.path.endswith('doLogout'):
            cpg.request.sessionMap['username'] = None
            cpg.threadData.user = None
            cpg.response.body = httptools.redirect('/')
        elif cpg.request.path.endswith('doLogin'):
            fromPage = cpg.request.paramMap['fromPage']
            login = cpg.request.paramMap['login']
            password = cpg.request.paramMap['password']
            errorMsg = self.checkLoginAndPassword(login, password)
            if errorMsg:
                cpg.response.body = loginScreen(fromPage, login = login, errorMsg = errorMsg)
            else:
                cpg.request.sessionMap['username'] = login
                cpg.response.body = httptools.redirect(fromPage)
            return

        # Check if user is logged in
        if (not cpg.request.sessionMap.get('username')) and self.notLoggedIn:
            self.notLoggedIn()
        if not cpg.request.sessionMap.get('username'):
            cpg.response.body = loginScreen(cpg.request.browserUrl)
            return

        # Everything is OK: user is logged in
        if self.loadUserByUsername:
            username = cpg.request.sessionMap['username']
            cpg.threadData.user = self.loadUserByUsername(username)
        
