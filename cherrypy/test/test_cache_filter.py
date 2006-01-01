import test
test.prefer_parent_path()

import cherrypy
import time


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

if __name__ == '__main__':
    helper.testmain()

