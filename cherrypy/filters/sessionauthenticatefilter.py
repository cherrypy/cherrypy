import cherrypy
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
    Filter allows for simple forms based authentication and access control
    """
    
    def beforeMain(self):
        if not cherrypy.config.get('sessionAuthenticateFilter.on', False):
            return
        
        
        checkLoginAndPassword = cherrypy.config.get('sessionAuthenticateFilter.checkLoginAndPassword', defaultCheckLoginAndPassword)
        loginScreen = cherrypy.config.get('sessionAuthenticateFilter.loginScreen', defaultLoginScreen)
        notLoggedIn = cherrypy.config.get('sessionAuthenticateFilter.notLoggedIn')
        loadUserByUsername = cherrypy.config.get('sessionAuthenticateFilter.loadUserByUsername')
        sessionKey = cherrypy.config.get('sessionAuthenticateFilter.sessionKey', 'username')

        if cherrypy.request.path.endswith('loginScreen'):
            return
        elif cherrypy.request.path.endswith('doLogout'):
            cherrypy.session[sessionKey] = None
            cherrypy.request.user = None
            fromPage = cherrypy.request.paramMap.get('fromPage', '..')
            raise cherrypy.HTTPRedirect(fromPage)
        elif cherrypy.request.path.endswith('doLogin'):
            fromPage = cherrypy.request.paramMap.get('fromPage', '..')
            login = cherrypy.request.paramMap['login']
            password = cherrypy.request.paramMap['password']
            errorMsg = checkLoginAndPassword(login, password)
            if errorMsg:
                cherrypy.response.body = loginScreen(fromPage, login = login, errorMsg = errorMsg)
                cherrypy.request.executeMain = False
            else:
                cherrypy.session[sessionKey] = login
                if not fromPage:
                    fromPage = '/'
                raise cherrypy.HTTPRedirect(fromPage)
            return

        # Check if user is logged in
        if (not cherrypy.session.get(sessionKey)) and notLoggedIn:
            # Call notLoggedIn so that applications where anynymous user
            #   is OK can handle it
            notLoggedIn()
        if not cherrypy.session.get(sessionKey):
            cherrypy.response.body = loginScreen(cherrypy.request.browserUrl)
            cherrypy.request.executeMain = False
            return
        
        # Everything is OK: user is logged in
        if loadUserByUsername:
            username = cherrypy.session[sessionKey]
            cherrypy.request.user = loadUserByUsername(username)
            cherrypy.threadData.user = loadUserByUsername(username)
