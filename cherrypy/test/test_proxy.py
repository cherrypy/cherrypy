from cherrypy.test import test
test.prefer_parent_path()

import cherrypy

script_names = ["", "/path/to/myapp"]

def setup_server():
    class Root:
        def index(self):
            raise cherrypy.HTTPRedirect('dummy')
        index.exposed = True
        
        def remoteip(self):
            return cherrypy.request.remote.ip
        remoteip.exposed = True
        
        def xhost(self):
            raise cherrypy.HTTPRedirect('blah')
        xhost.exposed = True
        xhost._cp_config = {'tools.proxy.local': 'X-Host'}
        
        def base(self):
            return cherrypy.request.base
        base.exposed = True
        
        def newurl(self):
            return ("Browse to <a href='%s'>this page</a>."
                    % cherrypy.tree.url("/this/new/page"))
        newurl.exposed = True
    
    for sn in script_names:
        cherrypy.tree.mount(Root(), sn)
    
    cherrypy.config.update({
        'environment': 'test_suite',
        'tools.proxy.on': True,
        'tools.proxy.base': 'www.mydomain.com',
        })


from cherrypy.test import helper

class ProxyTest(helper.CPWebCase):
    
    def testProxy(self):
        self.getPage("/")
        self.assertHeader('Location',
                          "http://www.mydomain.com%s/dummy" % self.prefix())
        
        # Test X-Forwarded-Host (Apache 1.3.33+ and Apache 2)
        self.getPage("/", headers=[('X-Forwarded-Host', 'http://www.yetanother.com')])
        self.assertHeader('Location', "http://www.yetanother.com/dummy")
        self.getPage("/", headers=[('X-Forwarded-Host', 'www.yetanother.com')])
        self.assertHeader('Location', "http://www.yetanother.com/dummy")
        
        # Test X-Forwarded-For (Apache2)
        self.getPage("/remoteip",
                     headers=[('X-Forwarded-For', '192.168.0.20')])
        self.assertBody("192.168.0.20")
        self.getPage("/remoteip",
                     headers=[('X-Forwarded-For', '67.15.36.43, 192.168.0.20')])
        self.assertBody("192.168.0.20")
        
        # Test X-Host (lighttpd; see https://trac.lighttpd.net/trac/ticket/418)
        self.getPage("/xhost", headers=[('X-Host', 'www.yetanother.com')])
        self.assertHeader('Location', "http://www.yetanother.com/blah")
        
        # Test X-Forwarded-Proto (lighttpd)
        self.getPage("/base", headers=[('X-Forwarded-Proto', 'https')])
        self.assertBody("https://www.mydomain.com")
        
        # Test tree.url()
        for sn in script_names:
            self.getPage(sn + "/newurl")
            self.assertBody("Browse to <a href='http://www.mydomain.com"
                            + sn + "/this/new/page'>this page</a>.")
            self.getPage(sn + "/newurl", headers=[('X-Forwarded-Host',
                                                   'http://www.yetanother.com')])
            self.assertBody("Browse to <a href='http://www.yetanother.com"
                            + sn + "/this/new/page'>this page</a>.")


if __name__ == '__main__':
    setup_server()
    helper.testmain()
