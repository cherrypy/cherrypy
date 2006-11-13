
from cherrypy.test import test
test.prefer_parent_path()

import cherrypy

def setup_server():
    class Root:
        def index(self):
            return "Hello, world"
        index.exposed = True
        
        def dom4(self):
            return "Under construction"
        dom4.exposed = True
        
        def method(self, value):
            return "You sent %s" % repr(value)
        method.exposed = True
    
    class VHost:
        def __init__(self, sitename):
            self.sitename = sitename
        
        def index(self):
            return "Welcome to %s" % self.sitename
        index.exposed = True
        
        def vmethod(self, value):
            return "You sent %s" % repr(value)
        vmethod.exposed = True
        
        def url(self):
            return cherrypy.url("nextpage")
        url.exposed = True
    
    
    root = Root()
    root.mydom2 = VHost("Domain 2")
    root.mydom3 = VHost("Domain 3")
    cherrypy.tree.mount(root)
    
    cherrypy.config.update({
        'environment': 'test_suite',
        'tools.virtual_host.on': True,
        'tools.virtual_host.www.mydom2.com': '/mydom2',
        'tools.virtual_host.www.mydom3.com': '/mydom3',
        'tools.virtual_host.www.mydom4.com': '/dom4',
        })

from cherrypy.test import helper

class VirtualHostTest(helper.CPWebCase):
    
    def testVirtualHost(self):
        self.getPage("/", [('Host', 'www.mydom1.com')])
        self.assertBody('Hello, world')
        self.getPage("/mydom2/", [('Host', 'www.mydom1.com')])
        self.assertBody('Welcome to Domain 2')
        
        self.getPage("/", [('Host', 'www.mydom2.com')])
        self.assertBody('Welcome to Domain 2')
        self.getPage("/", [('Host', 'www.mydom3.com')])
        self.assertBody('Welcome to Domain 3')
        self.getPage("/", [('Host', 'www.mydom4.com')])
        self.assertBody('Under construction')
        
        # Test GET, POST, and positional params
        self.getPage("/method?value=root")
        self.assertBody("You sent 'root'")
        self.getPage("/vmethod?value=dom2+GET", [('Host', 'www.mydom2.com')])
        self.assertBody("You sent 'dom2 GET'")
        self.getPage("/vmethod", [('Host', 'www.mydom3.com')], method="POST",
                     body="value=dom3+POST")
        self.assertBody("You sent 'dom3 POST'")
        self.getPage("/vmethod/pos", [('Host', 'www.mydom3.com')])
        self.assertBody("You sent 'pos'")
        
        self.getPage("/url", [('Host', 'www.mydom2.com')])
        self.assertBody("http://www.mydom2.com/nextpage")


if __name__ == "__main__":
    setup_server()
    helper.testmain()
