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
    
    def before_main(self):
        if not cherrypy.config.get('session_authenticate_filter.on', False):
            return
        
        
        checkLoginAndPassword = cherrypy.config.get('session_authenticate_filter.check_login_and_password', defaultCheckLoginAndPassword)
        loginScreen = cherrypy.config.get('session_authenticate_filter.login_screen', defaultLoginScreen)
        notLoggedIn = cherrypy.config.get('session_authenticate_filter.not_logged_in')
        loadUserByUsername = cherrypy.config.get('session_authenticate_filter.load_user_by_username')
        sessionKey = cherrypy.config.get('session_authenticate_filter.session_key', 'username')

        if cherrypy.request.path.endswith('loginScreen'):
            return
        elif cherrypy.request.path.endswith('doLogout'):
            cherrypy.session[sessionKey] = None
            cherrypy.request.user = None
            fromPage = cherrypy.request.params.get('fromPage', '..')
            raise cherrypy.HTTPRedirect(fromPage)
        elif cherrypy.request.path.endswith('doLogin'):
            fromPage = cherrypy.request.params.get('fromPage', '..')
            login = cherrypy.request.params['login']
            password = cherrypy.request.params['password']
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
