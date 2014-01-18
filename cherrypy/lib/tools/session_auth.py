"""Functions for builtin CherryPy tools."""

import cherrypy
from cherrypy.lib._cpcompat import unicodestr
from cherrypy.lib.tools import HandlerTool


class SessionAuth(object):

    """Assert that the user is logged in."""

    session_key = "username"
    debug = False

    def check_username_and_password(self, username, password):
        pass

    def anonymous(self):
        """Provide a temporary user name for anonymous users."""
        pass

    def on_login(self, username):
        pass

    def on_logout(self, username):
        pass

    def on_check(self, username):
        pass

    def login_screen(self, from_page='..', username='', error_msg='',
                     **kwargs):
        return (unicodestr("""<html><body>
Message: %(error_msg)s
<form method="post" action="do_login">
    Login: <input type="text" name="username" value="%(username)s" size="10" />
    <br />
    Password: <input type="password" name="password" size="10" />
    <br />
    <input type="hidden" name="from_page" value="%(from_page)s" />
    <br />
    <input type="submit" />
</form>
</body></html>""") % vars()).encode("utf-8")

    def do_login(self, username, password, from_page='..', **kwargs):
        """Login. May raise redirect, or return True if request handled."""
        response = cherrypy.serving.response
        error_msg = self.check_username_and_password(username, password)
        if error_msg:
            body = self.login_screen(from_page, username, error_msg)
            response.body = body
            if "Content-Length" in response.headers:
                # Delete Content-Length header so finalize() recalcs it.
                del response.headers["Content-Length"]
            return True
        else:
            cherrypy.serving.request.login = username
            cherrypy.session[self.session_key] = username
            self.on_login(username)
            raise cherrypy.HTTPRedirect(from_page or "/")

    def do_logout(self, from_page='..', **kwargs):
        """Logout. May raise redirect, or return True if request handled."""
        sess = cherrypy.session
        username = sess.get(self.session_key)
        sess[self.session_key] = None
        if username:
            cherrypy.serving.request.login = None
            self.on_logout(username)
        raise cherrypy.HTTPRedirect(from_page)

    def do_check(self):
        """Assert username. Raise redirect, or return True if request handled.
        """
        sess = cherrypy.session
        request = cherrypy.serving.request
        response = cherrypy.serving.response

        username = sess.get(self.session_key)
        if not username:
            sess[self.session_key] = username = self.anonymous()
            if self.debug:
                cherrypy.log(
                    'No session[username], trying anonymous', 'TOOLS.SESSAUTH')
        if not username:
            url = cherrypy.url(qs=request.query_string)
            if self.debug:
                cherrypy.log('No username, routing to login_screen with '
                             'from_page %r' % url, 'TOOLS.SESSAUTH')
            response.body = self.login_screen(url)
            if "Content-Length" in response.headers:
                # Delete Content-Length header so finalize() recalcs it.
                del response.headers["Content-Length"]
            return True
        if self.debug:
            cherrypy.log('Setting request.login to %r' %
                         username, 'TOOLS.SESSAUTH')
        request.login = username
        self.on_check(username)

    def run(self):
        request = cherrypy.serving.request
        response = cherrypy.serving.response

        path = request.path_info
        if path.endswith('login_screen'):
            if self.debug:
                cherrypy.log('routing %r to login_screen' %
                             path, 'TOOLS.SESSAUTH')
            return self.login_screen(**request.params)
        elif path.endswith('do_login'):
            if request.method != 'POST':
                response.headers['Allow'] = "POST"
                if self.debug:
                    cherrypy.log('do_login requires POST', 'TOOLS.SESSAUTH')
                raise cherrypy.HTTPError(405)
            if self.debug:
                cherrypy.log('routing %r to do_login' % path, 'TOOLS.SESSAUTH')
            return self.do_login(**request.params)
        elif path.endswith('do_logout'):
            if request.method != 'POST':
                response.headers['Allow'] = "POST"
                raise cherrypy.HTTPError(405)
            if self.debug:
                cherrypy.log('routing %r to do_logout' %
                             path, 'TOOLS.SESSAUTH')
            return self.do_logout(**request.params)
        else:
            if self.debug:
                cherrypy.log('No special path, running do_check',
                             'TOOLS.SESSAUTH')
            return self.do_check()


def session_auth(**kwargs):
    sa = SessionAuth()
    for k, v in kwargs.items():
        setattr(sa, k, v)
    return sa.run()
session_auth.__doc__ = """Session authentication hook.

Any attribute of the SessionAuth class may be overridden via a keyword arg
to this function:

""" + "\n".join(["%s: %s" % (k, type(getattr(SessionAuth, k)).__name__)
                 for k in dir(SessionAuth) if not k.startswith("__")])


class SessionAuthTool(HandlerTool):

    def _setargs(self):
        for name in dir(SessionAuth):
            if not name.startswith("__"):
                setattr(self, name, None)
