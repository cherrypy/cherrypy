import test
test.prefer_parent_path()

import cherrypy, os


def setup_server():
    class Root:
        
        _cp_config = {'tools.sessions.on': True,
                      'tools.sessions.storage_type' : 'file',
                      'tools.sessions.storage_path' : '.',
                      }
        
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
        
        def setsessiontype(self, newtype):
            cherrypy.config.update({'tools.sessions.storage_type': newtype})
        setsessiontype.exposed = True
        
    cherrypy.tree.mount(Root())
    cherrypy.config.update({
            'log_to_screen': False,
            'environment': 'production',
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
        self.getPage('/setsessiontype/file')
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
    setup_server()
    helper.testmain()

