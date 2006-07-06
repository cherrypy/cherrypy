import test
test.prefer_parent_path()

import cherrypy
import time


def setup_server():
    class Root:
        
        _cp_config = {'tools.caching.on': True}
        
        def __init__(self):
            cherrypy.counter = 0
        
        def index(self):
            cherrypy.counter += 1
            msg = "visit #%s" % cherrypy.counter
            return msg
        index.exposed = True
    
    cherrypy.tree.mount(Root())
    cherrypy.config.update({
        'log_to_screen': False,
        'environment': 'production',
    })


import helper

class CacheTest(helper.CPWebCase):
    
    def testCaching(self):
        elapsed = 0.0
        for trial in xrange(10):
            self.getPage("/")
            # The response should be the same every time,
            # except for the Age response header.
            self.assertBody('visit #1')
            if trial != 0:
                age = int(self.assertHeader("Age"))
                self.assert_(age >= elapsed)
                elapsed = age
        
        # POST, PUT, DELETE should not be cached.
        self.getPage("/", method="POST")
        self.assertBody('visit #2')
        self.getPage("/", method="GET")
        self.assertBody('visit #2')
        self.getPage("/", method="DELETE")
        self.assertBody('visit #3')


if __name__ == '__main__':
    setup_server()
    helper.testmain()

