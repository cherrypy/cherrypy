import test
test.prefer_parent_path()

import cherrypy
import time


def setup_server():
    class Root:
        def __init__(self):
            cherrypy.counter = 0
        
        def index(self):
            cherrypy.counter += 1
            msg = "visit #%s" % cherrypy.counter
            return msg
        index.exposed = True

    cherrypy.root = Root()
    cherrypy.config.update({
            'server.log_to_screen': False,
            'server.environment': 'production',
            'cache_filter.on': True,
    })


import helper

class CacheFilterTest(helper.CPWebCase):
    
    def testCaching(self):
        for trial in xrange(10):
            self.getPage("/")
            # The response should be the same every time!
            self.assertBody('visit #1')
        
        # POST, PUT, DELETE should not be cached.
        self.getPage("/", method="POST")
        self.assertBody('visit #2')
        # The previous request should have invalidated the cache,
        # so this request will recalc the response.
        self.getPage("/", method="GET")
        self.assertBody('visit #3')
        # ...but this request should get the cached copy.
        self.getPage("/", method="GET")
        self.assertBody('visit #3')
        self.getPage("/", method="DELETE")
        self.assertBody('visit #4')
        # The previous request should have invalidated the cache,
        # so this request will recalc the response.
        self.getPage("/", method="GET")
        self.assertBody('visit #5')


if __name__ == '__main__':
    setup_server()
    helper.testmain()

