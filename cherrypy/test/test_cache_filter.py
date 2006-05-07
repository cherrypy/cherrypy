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

class CacheFilterTest(helper.CPWebCase):
    
    def testCaching(self):
        for trial in xrange(10):
            self.getPage("/")
            # The response should be the same every time!
            self.assertBody('visit #1')

if __name__ == '__main__':
    setup_server()
    helper.testmain()

