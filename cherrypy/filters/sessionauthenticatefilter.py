import cherrypy
from basefilter import BaseFilter


def defaultLoginScreen(from_page, login = '', errorMsg = ''):
    return """
    <html><body>
        Message: %s
        <form method="post" action="do_login">
            Login: <input type="text" name="login" value="%s" size="10"/><br/>
            Password: <input type="password" name="password" size="10"/><br/>
            <input type="hidden" name="from_page" value="%s"/><br/>
            <input type="submit"/>
        </form>
    </body></html>
    """ % (errorMsg, login, from_page)

def defaultCheckLoginAndPassword(login, password):
    # Dummy checkLoginAndPassword function
    if login != 'login' or password != 'password':
        return u'Wrong login/password'

class SessionAuthenticateFilter(BaseFilter):
    """
    Filter allows for simple forms based authentication and access control
    """
    
    def before_main(self):
        conf = cherrypy.config.get
        if ((not conf('session_authenticate_filter.on', False))
              or conf('static_filter.on', False)):
            return
        
        checkLoginAndPassword = cherrypy.config.get('session_authenticate_filter.check_login_and_password', defaultCheckLoginAndPassword)
        loginScreen = cherrypy.config.get('session_authenticate_filter.login_screen', defaultLoginScreen)
        notLoggedIn = cherrypy.config.get('session_authenticate_filter.not_logged_in')
        loadUserByUsername = cherrypy.config.get('session_authenticate_filter.load_user_by_username')
        sessionKey = cherrypy.config.get('session_authenticate_filter.session_key', 'username')

        if cherrypy.request.path.endswith('loginScreen'):
            return
        elif cherrypy.request.path.endswith('do_logout'):
            cherrypy.session[sessionKey] = None
            cherrypy.request.user = None
            from_page = cherrypy.request.params.get('from_page', '..')
            raise cherrypy.HTTPRedirect(from_page)
        elif cherrypy.request.path.endswith('do_login'):
            from_page = cherrypy.request.params.get('from_page', '..')
            login = cherrypy.request.params['login']
            password = cherrypy.request.params['password']
            errorMsg = checkLoginAndPassword(login, password)
            if errorMsg:
                cherrypy.response.body = loginScreen(from_page, login = login, errorMsg = errorMsg)
                cherrypy.request.executeMain = False
            else:
                cherrypy.session[sessionKey] = login
                if not from_page:
                    from_page = '/'
                raise cherrypy.HTTPRedirect(from_page)
            return

        # Check if user is logged in
        if (not cherrypy.session.get(sessionKey)) and notLoggedIn:
            # Call notLoggedIn so that applications where anynymous user
            #   is OK can handle it
            notLoggedIn()
        if not cherrypy.session.get(sessionKey):
            cherrypy.response.body = loginScreen(cherrypy.request.browser_url)
            cherrypy.request.executeMain = False
            return
        
        # Everything is OK: user is logged in
        if loadUserByUsername:
            username = cherrypy.session[sessionKey]
            cherrypy.request.user = loadUserByUsername(username)
            cherrypy.threadData.user = loadUserByUsername(username)
