import test
test.prefer_parent_path()

import cherrypy
from cherrypy.filters.cachefilter import expires


def setup_server():
    class Root:
        def __init__(self):
            cherrypy.counter = 0
        
        def index(self):
            cherrypy.counter += 1
            msg = "visit #%s" % cherrypy.counter
            return msg
        index.exposed = True
    
    class UnCached(object):
        
        use_force = False
        
        def force(self):
            self.use_force = True
            expires(force=self.use_force)
            return "being forceful"
        force.exposed = True
        
        def dynamic(self):
            cherrypy.response.headers['Cache-Control'] = 'private'
            expires(force=self.use_force)
            return "D-d-d-dynamic!"
        dynamic.exposed = True
        
        def cacheable(self):
            cherrypy.response.headers['Etag'] = 'bibbitybobbityboo'
            expires(force=self.use_force)
            return "Hi, I'm cacheable."
        cacheable.exposed = True
        
        def specific(self):
            expires(secs=86400, force=self.use_force)
            return "I am being specific"
        specific.exposed = True
    
    cherrypy.root = Root()
    cherrypy.root.expires = UnCached()
    cherrypy.config.update({
        'global': {'server.log_to_screen': False,
                   'server.environment': 'production',
                   'cache_filter.on': True,
                   },
        '/expires': {'cache_filter.on': False},
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
    
    def testExpiresTool(self):
        
        # test setting an expires header
        self.getPage("/expires/specific")
        self.assertStatus("200 OK")
        self.assertHeader("Expires")
        
        # dynamic content that sets indicators should not have
        # "cache prevention" headers
        self.getPage("/expires/cacheable")
        self.assertStatus("200 OK")
        self.assertNoHeader("Pragma")
        self.assertNoHeader("Cache-Control")
        
        self.getPage('/expires/dynamic')
        self.assertBody("D-d-d-dynamic!")
        # the Cache-Control header should be untouched
        self.assertHeader("Cache-Control", "private")
        
        # configure the tool to ignore indicators and replace existing headers
        self.getPage("/expires/force")
        self.assertStatus("200 OK")
        # This also gives us a chance to test 0 expiry with no other headers
        self.assertHeader("Pragma", "no-cache")
        conf = cherrypy.config.get
        if conf('server.protocol_version', '') == "HTTP/1.1":
            self.assertHeader("Cache-Control", "no-cache")
        d = self.assertHeader("Date")
        self.assertHeader("Expires", d)
        
        # the cacheable handler should now have "cache prevention" headers
        self.getPage("/expires/cacheable")
        self.assertStatus("200 OK")
        self.assertHeader("Pragma", "no-cache")
        if conf('server.protocol_version', '') == "HTTP/1.1":
            self.assertHeader("Cache-Control", "no-cache")
        d = self.assertHeader("Date")
        self.assertHeader("Expires", d)
        
        self.getPage('/expires/dynamic')
        self.assertBody("D-d-d-dynamic!")
        # dynamic sets Cache-Control to private but it should  be
        # overwritten here ...
        self.assertHeader("Pragma", "no-cache")
        if conf('server.protocol_version', '') == "HTTP/1.1":
            self.assertHeader("Cache-Control", "no-cache")
        d = self.assertHeader("Date")
        self.assertHeader("Expires", d)


if __name__ == '__main__':
    setup_server()
    helper.testmain()

