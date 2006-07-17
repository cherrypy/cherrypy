import test
test.prefer_parent_path()

import os
curdir = os.path.join(os.getcwd(), os.path.dirname(__file__))

import cherrypy
import datetime
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

    class UnCached(object):
        _cp_config = {'tools.expires.on': True,
                      'tools.staticdir.on': True,
                      'tools.staticdir.dir': 'static',
                      'tools.staticdir.root': curdir,
                      }

        def gentle(self):
            self._cp_config['tools.expires.force'] = False
            return "being forceful"
        gentle.exposed = True

        def ignorant(self):
            self._cp_config['tools.expires.ignore_indicators'] = True
            return "being ignorant"
        ignorant.exposed = True

        def dynamic(self):
            cherrypy.response.headers['Cache-Control'] = 'private'
            return "D-d-d-dynamic!"
        dynamic.exposed = True

        def cacheable(self):
            cherrypy.response.headers['Etag'] = 'bibbitybobbityboo'
            return "Hi, I'm cacheable."
        cacheable.exposed = True

        expire_on = datetime.datetime(2006, 7, 17, 8, 55, 59, 171000)

        def specific(self):
            return "I am being specific"
        specific.exposed = True
        specific._cp_config = {'tools.expires.e_time': expire_on}

        class Foo(object):pass
        
        def wrongtype(self):
            return "Woops"
        wrongtype.exposed = True
        wrongtype._cp_config = {'tools.expires.e_time': Foo()}

        def wrongvalue(self):
            return "Uh oh"
        wrongvalue.exposed = True
        wrongvalue._cp_config = {'tools.expires.e_time': 42}


    cherrypy.tree.mount(Root())
    cherrypy.tree.mount(UnCached(), "/expires")
    cherrypy.config.update({
        'log_to_screen': False,
        'environment': 'production',
        'show_tracebacks': True,
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

    def testExpiresTool(self):

        # test setting a specific expires header
        self.getPage("/expires/specific")
        self.assertStatus("200 OK")
        self.assertHeader("Expires", "Mon, 17 Jul 2006 12:55:59 GMT")

        # test exceptions for bad e_time values
        self.getPage("/expires/wrongtype")
        self.assertStatus("500 Internal error")
        self.assertInBody("TypeError")

        self.getPage("/expires/wrongvalue")
        self.assertStatus("500 Internal error")
        self.assertInBody("ValueError")

        self.getPage('/expires/dynamic')
        self.assertBody("D-d-d-dynamic!")
        # dynamic sets Cache-Control to private but it should  be
        # overwritten here ...
        self.assertHeader("Cache-Control", "no-cache")
        self.assertHeader("Expires", "0")
        self.assertHeader("Pragma", "no-cache")

        # configure the tool to keep existing headers
        self.getPage("/expires/gentle")
        self.assertStatus("200 OK")

        self.getPage('/expires/dynamic')
        self.assertBody("D-d-d-dynamic!")
        # the Cache-Control header should now be untouched
        self.assertHeader("Cache-Control", "private")

        # static content should not have "cache prevention" headers
        self.getPage("/expires/index.html")
        self.assertStatus("200 OK")
        self.assertNoHeader("Pragma")
        self.assertNoHeader("Cache-Control")
        self.assertNoHeader("Expires")

        # dynamic content that sets indicators should not have
        # "cache prevention" headers
        self.getPage("/expires/cacheable")
        self.assertStatus("200 OK")
        self.assertNoHeader("Pragma")
        self.assertNoHeader("Cache-Control")
        self.assertNoHeader("Expires")

        # configure the tool to ignore indicators
        self.getPage("/expires/ignorant")
        self.assertStatus("200 OK")

        # static content should now have "cache prevention" headers
        self.getPage("/expires/index.html")
        self.assertStatus("200 OK")
        self.assertHeader("Pragma", "no-cache")
        self.assertHeader("Cache-Control", "no-cache")
        self.assertHeader("Expires", "0")

        # the cacheable handler should now have "cache prevention" headers
        self.getPage("/expires/cacheable")
        self.assertStatus("200 OK")
        self.assertHeader("Pragma", "no-cache")
        self.assertHeader("Cache-Control", "no-cache")
        self.assertHeader("Expires", "0")

if __name__ == '__main__':
    setup_server()
    helper.testmain()

