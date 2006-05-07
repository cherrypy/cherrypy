import test
test.prefer_parent_path()

import cherrypy

def setup_server():
    class Test:
        def index(self):
            return "Hi, you are logged in"
        index.exposed = True
    
    cherrypy.root = Test()
    
    def check(login, password):
        # Dummy check_login_and_password function
        if login != 'login' or password != 'password':
            return u'Wrong login/password'
    
    cherrypy.config.update({
            'log_to_screen': False,
            'environment': 'production',
            'tools.sessions.on': True,
            '/': {
                'tools.session_auth.on': True,
                'tools.session_auth.check_login_and_password': check,
                },
            })


import helper

class SessionAuthenticateFilterTest(helper.CPWebCase):
    
    def testSessionAuthenticateFilter(self):
        # request a page and check for login form
        self.getPage('/')
        self.assertInBody('<form method="post" action="do_login">')

        # setup credentials
        login_body = 'login=login&password=password&from_page=/'

        # attempt a login
        self.getPage('/do_login', method='POST', body=login_body)
        self.assert_(self.status in ('302 Found', '303 See Other'))

        # get the page now that we are logged in
        self.getPage('/', self.cookies)
        self.assertBody('Hi, you are logged in')

        # do a logout
        self.getPage('/do_logout', self.cookies)
        self.assert_(self.status in ('302 Found', '303 See Other'))

        # verify we are logged out
        self.getPage('/', self.cookies)
        self.assertInBody('<form method="post" action="do_login">')


if __name__ == "__main__":
    setup_server()
    helper.testmain()

