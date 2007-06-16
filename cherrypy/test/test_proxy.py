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
        xhost._cp_config = {'tools.proxy.local': 'X-Host',
                            'tools.trailing_slash.extra': True,
                            }
        
        def base(self):
            return cherrypy.request.base
        base.exposed = True
        
        def newurl(self):
            return ("Browse to <a href='%s'>this page</a>."
                    % cherrypy.url("/this/new/page"))
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
                          "%s://www.mydomain.com%s/dummy" %
                          (self.scheme, self.prefix()))
        
        # Test X-Forwarded-Host (Apache 1.3.33+ and Apache 2)
        self.getPage("/", headers=[('X-Forwarded-Host', 'http://www.example.com')])
        self.assertHeader('Location', "http://www.example.com/dummy")
        self.getPage("/", headers=[('X-Forwarded-Host', 'www.example.com')])
        self.assertHeader('Location', "%s://www.example.com/dummy" % self.scheme)
        
        # Test X-Forwarded-For (Apache2)
        self.getPage("/remoteip",
                     headers=[('X-Forwarded-For', '192.168.0.20')])
        self.assertBody("192.168.0.20")
        self.getPage("/remoteip",
                     headers=[('X-Forwarded-For', '67.15.36.43, 192.168.0.20')])
        self.assertBody("192.168.0.20")
        
        # Test X-Host (lighttpd; see https://trac.lighttpd.net/trac/ticket/418)
        self.getPage("/xhost", headers=[('X-Host', 'www.example.com')])
        self.assertHeader('Location', "%s://www.example.com/blah" % self.scheme)
        
        # Test X-Forwarded-Proto (lighttpd)
        self.getPage("/base", headers=[('X-Forwarded-Proto', 'https')])
        self.assertBody("https://www.mydomain.com")
        
        # Test cherrypy.url()
        for sn in script_names:
            # Test the value inside requests
            self.getPage(sn + "/newurl")
            self.assertBody("Browse to <a href='%s://www.mydomain.com" % self.scheme
                            + sn + "/this/new/page'>this page</a>.")
            self.getPage(sn + "/newurl", headers=[('X-Forwarded-Host',
                                                   'http://www.example.com')])
            self.assertBody("Browse to <a href='http://www.example.com"
                            + sn + "/this/new/page'>this page</a>.")
            
            # Test the value outside requests
            port = ""
            if self.scheme == "http" and self.PORT != 80:
                port = ":%s" % self.PORT
            elif self.scheme == "https" and self.PORT != 443:
                port = ":%s" % self.PORT
            host = self.HOST
            if host in ('0.0.0.0', '::'):
                import socket
                host = socket.gethostname()
            self.assertEqual(cherrypy.url("/this/new/page", script_name=sn),
                             "%s://%s%s%s/this/new/page"
                             % (self.scheme, host, port, sn))
        
        # Test trailing slash (see http://www.cherrypy.org/ticket/562).
        self.getPage("/xhost/", headers=[('X-Host', 'www.example.com')])
        self.assertHeader('Location', "%s://www.example.com/xhost"
                          % self.scheme)


if __name__ == '__main__':
    setup_server()
    helper.testmain()
