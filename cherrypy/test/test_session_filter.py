import test
test.prefer_parent_path()

import cherrypy, os, time
from cherrypy.filters import sessionfilter

localDir = os.path.dirname(__file__)

def setup_server():
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
        
        def setsessiontype(self, newtype):
            cherrypy.config.update({'session_filter.storage_type': newtype})
        setsessiontype.exposed = True

        def delete(self):
            cherrypy.session.delete() 
            sessionfilter.expire() 
            return "done" 
 	delete.exposed = True
        
    cherrypy.root = Root()
    cherrypy.config.update({
            'server.log_to_screen': False,
            'server.environment': 'production',
            'session_filter.on': True,
            'session_filter.storage_type' : 'file',
            'session_filter.storage_path' : localDir,
            'session_filter.timeout': 0.017,
            'session_filter.clean_up_delay': 0.017,
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

        self.getPage('/delete', self.cookies)
        self.assertBody("done")

        f = lambda: [x for x in os.listdir(localDir) if x.startswith('session-')] 
        self.assertEqual(f(), [])
        
        self.getPage('/setsessiontype/file')
        self.getPage('/testStr')
        self.assertBody('1')
        self.getPage('/testGen', self.cookies)
        self.assertBody('2')
        self.getPage('/testStr', self.cookies)
        self.assertBody('3')

        f = lambda: [x for x in os.listdir(localDir) if x.startswith('session-')]
        self.assertNotEqual(f(), [])
        
        self.getPage('/delete', self.cookies)
        self.assertBody("done")

        f = lambda: [x for x in os.listdir(localDir) if x.startswith('session-')] 
        self.assertEqual(f(), [])

        self.getPage('/testStr')
        f = lambda: [x for x in os.listdir(localDir) if x.startswith('session-')]
        self.assertNotEqual(f(), [])

        # Clean up session files
        for fname in os.listdir(localDir):
            if fname.startswith('session-'):
                os.unlink(os.path.join(localDir, fname))

if __name__ == "__main__":
    setup_server()
    helper.testmain()

