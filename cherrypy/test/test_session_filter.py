import test
test.prefer_parent_path()

import cherrypy, os

class Root:
    def testGen(self):
        counter = cherrypy.session.get('counter', 0) + 1
        cherrypy.session['counter'] = counter
        yield str(counter)
    testGen.exposed = True
    def testStr(self):
        counter = cherrypy.session.get('counter', 0) + 1
        cherrypy.session['counter'] = counter
        return str(counter)
    testStr.exposed = True
    
cherrypy.root = Root()
cherrypy.config.update({
        'server.log_to_screen': False,
        'server.environment': 'production',
        'session_filter.on': True,
        'session_filter.storage_type' : 'file',
        'session_filter.storage_path' : '.',
})

import helper

class SessionFilterTest(helper.CPWebCase):
    
    def testSessionFilter(self):
        self.getPage('/testStr')
        self.assertBody('1')
        self.getPage('/testGen', self.cookies)
        self.assertBody('2')
        self.getPage('/testStr', self.cookies)
        self.assertBody('3')
        cherrypy.config.update({
            'session_filter.storage_type' : 'file',
        })
        self.getPage('/testStr')
        self.assertBody('1')
        self.getPage('/testGen', self.cookies)
        self.assertBody('2')
        self.getPage('/testStr', self.cookies)
        self.assertBody('3')

        # Clean up session files
        for fname in os.listdir('.'):
            if fname.startswith('session-'):
                os.unlink(fname)
        
        
if __name__ == "__main__":
    helper.testmain()

