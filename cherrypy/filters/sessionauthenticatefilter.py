import cherrypy
from basefilter import BaseFilter


def default_login_screen(from_page, login = '', error_msg = ''):
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
    """ % (error_msg, login, from_page)

def default_check_login_and_password(login, password):
    # Dummy check_login_and_password function
    if login != 'login' or password != 'password':
        return u'Wrong login/password'

class SessionAuthenticateFilter(BaseFilter):
    """
    Filter allows for simple forms based authentication and access control
    """
    
    def before_main(self):
        cherrypy.request.user = None
        cherrypy.thread_data.user = None

        conf = cherrypy.config.get
        if ((not conf('session_authenticate_filter.on', False))
              or conf('static_filter.on', False)):
            return
        
        check_login_and_password = cherrypy.config.get('session_authenticate_filter.check_login_and_password', default_check_login_and_password)
        login_screen = cherrypy.config.get('session_authenticate_filter.login_screen', default_login_screen)
        not_logged_in = cherrypy.config.get('session_authenticate_filter.not_logged_in')
        load_user_by_username = cherrypy.config.get('session_authenticate_filter.load_user_by_username')
        session_key = cherrypy.config.get('session_authenticate_filter.session_key', 'username')
        on_login = cherrypy.config.get('session_authenticate_filter.on_login', None)
        on_logout = cherrypy.config.get('session_authenticate_filter.on_logout', None)

        if cherrypy.request.path.endswith('login_screen'):
            return
        elif cherrypy.request.path.endswith('do_logout'):
            login = cherrypy.session.get('session_key')
            cherrypy.session[session_key] = None
            cherrypy.request.user = None
            cherrypy.thread_data.user = None
            if login and on_logout:
                on_logout(login)
            from_page = cherrypy.request.params.get('from_page', '..')
            raise cherrypy.HTTPRedirect(from_page)
        elif cherrypy.request.path.endswith('do_login'):
            from_page = cherrypy.request.params.get('from_page', '..')
            login = cherrypy.request.params['login']
            password = cherrypy.request.params['password']
            error_msg = check_login_and_password(login, password)
            if error_msg:
                cherrypy.response.body = login_screen(from_page, login = login, error_msg = error_msg)
                cherrypy.request.execute_main = False
            else:
                cherrypy.session[session_key] = login
                if on_login:
                    on_login(login)
                if not from_page:
                    from_page = '/'
                raise cherrypy.HTTPRedirect(from_page)
            return

        # Check if user is logged in
        temp_user = None
        if (not cherrypy.session.get(session_key)) and not_logged_in:
            # Call not_logged_in so that applications where anynymous user
            #   is OK can handle it
            temp_user = not_logged_in()
        if (not cherrypy.session.get(session_key)) and not temp_user:
            cherrypy.response.body = login_screen(cherrypy.request.browser_url)
            cherrypy.request.execute_main = False
            return
        
        # Everything is OK: user is logged in
        if load_user_by_username and not cherrypy.thread_data.user:
            username = temp_user or cherrypy.session[session_key]
            cherrypy.request.user = load_user_by_username(username)
            cherrypy.thread_data.user = cherrypy.request.user
