from cherrypy.test import test
test.prefer_parent_path()

import os
curdir = os.path.join(os.getcwd(), os.path.dirname(__file__))

import cherrypy


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

    class UnCached(object):
        _cp_config = {'tools.expires.on': True,
                      'tools.staticdir.on': True,
                      'tools.staticdir.dir': 'static',
                      'tools.staticdir.root': curdir,
                      }

        def force(self):
            self._cp_config['tools.expires.force'] = True
            return "being forceful"
        force.exposed = True

        def dynamic(self):
            cherrypy.response.headers['Cache-Control'] = 'private'
            return "D-d-d-dynamic!"
        dynamic.exposed = True

        def cacheable(self):
            cherrypy.response.headers['Etag'] = 'bibbitybobbityboo'
            return "Hi, I'm cacheable."
        cacheable.exposed = True

        def specific(self):
            return "I am being specific"
        specific.exposed = True
        specific._cp_config = {'tools.expires.secs': 86400}

        class Foo(object):pass
        
        def wrongtype(self):
            return "Woops"
        wrongtype.exposed = True
        wrongtype._cp_config = {'tools.expires.secs': Foo()}
    
    cherrypy.tree.mount(Root())
    cherrypy.tree.mount(UnCached(), "/expires")
    cherrypy.config.update({'environment': 'test_suite'})


from cherrypy.test import helper

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

    def testExpiresTool(self):
        
        # test setting an expires header
        self.getPage("/expires/specific")
        self.assertStatus("200 OK")
        self.assertHeader("Expires")
        
        # test exceptions for bad time values
        self.getPage("/expires/wrongtype")
        self.assertStatus(500)
        self.assertInBody("TypeError")
        
        # static content should not have "cache prevention" headers
        self.getPage("/expires/index.html")
        self.assertStatus("200 OK")
        self.assertNoHeader("Pragma")
        self.assertNoHeader("Cache-Control")
        
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
        if cherrypy.config.get('server.protocol_version') == "HTTP/1.1":
            self.assertHeader("Cache-Control", "no-cache")
        d = self.assertHeader("Date")
        self.assertHeader("Expires", d)
        
        # static content should now have "cache prevention" headers
        self.getPage("/expires/index.html")
        self.assertStatus("200 OK")
        self.assertHeader("Pragma", "no-cache")
        if cherrypy.config.get('server.protocol_version') == "HTTP/1.1":
            self.assertHeader("Cache-Control", "no-cache")
        d = self.assertHeader("Date")
        self.assertHeader("Expires", d)
        
        # the cacheable handler should now have "cache prevention" headers
        self.getPage("/expires/cacheable")
        self.assertStatus("200 OK")
        self.assertHeader("Pragma", "no-cache")
        if cherrypy.config.get('server.protocol_version') == "HTTP/1.1":
            self.assertHeader("Cache-Control", "no-cache")
        d = self.assertHeader("Date")
        self.assertHeader("Expires", d)
        
        self.getPage('/expires/dynamic')
        self.assertBody("D-d-d-dynamic!")
        # dynamic sets Cache-Control to private but it should  be
        # overwritten here ...
        self.assertHeader("Pragma", "no-cache")
        if cherrypy.config.get('server.protocol_version') == "HTTP/1.1":
            self.assertHeader("Cache-Control", "no-cache")
        d = self.assertHeader("Date")
        self.assertHeader("Expires", d)

if __name__ == '__main__':
    setup_server()
    helper.testmain()

