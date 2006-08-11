import test
test.prefer_parent_path()

import cherrypy


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
    
    cherrypy.tree.mount(Root())
    cherrypy.config.update({
            'environment': 'production',
            'log_to_screen': False,
            'tools.proxy.on': True,
            'tools.proxy.base': 'http://www.mydomain.com',
    })


import helper

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
        self.getPage("/xhost", headers=[('X-Host', 'http://www.yetanother.com')])
        self.assertHeader('Location', "http://www.yetanother.com/blah")


if __name__ == '__main__':
    setup_server()
    helper.testmain()
