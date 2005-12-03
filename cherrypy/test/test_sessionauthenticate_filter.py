import test
test.prefer_parent_path()

import cherrypy

class Test:
    def index(self):
        return "Hi, you are logged in"
    index.exposed = True

cherrypy.root = Test()

cherrypy.config.update({
        'server.log_to_screen': False,
        'server.environment': 'production',
        'session_filter.on': True,
})

cherrypy.config.update({'/':
                        {'session_authenticate_filter.on':True,
                         }
                        })
import helper

class SessionAuthenticateFilterTest(helper.CPWebCase):
    
    def testSessionAuthenticateFilter(self):
        protocol = cherrypy.config.get('server.protocol_version')
        # request a page and check for login form
        self.getPage('/')
        self.assertInBody('<form method="post" action="doLogin">')

        # setup credentials        
        login_body = 'login=login&password=password&fromPage=/'

        # attempt a login
        self.getPage('/doLogin', method='POST', body=login_body)
        if protocol == 'HTTP/1.0':
            self.assertStatus('302 Found')
        else:
            self.assertStatus('303 See Other')

        # get the page now that we are logged in
        self.getPage('/', self.cookies)
        self.assertBody('Hi, you are logged in')

        # do a logout
        self.getPage('/doLogout', self.cookies)
        if protocol == 'HTTP/1.0':
            self.assertStatus('302 Found')
        else:
            self.assertStatus('303 See Other')

        # verify we are logged out
        self.getPage('/', self.cookies)
        self.assertInBody('<form method="post" action="doLogin">')
        
        
if __name__ == "__main__":
    helper.testmain()

