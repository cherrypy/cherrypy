
import test
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
    
    class VHost:
        def __init__(self, sitename):
            self.sitename = sitename
        
        def index(self):
            return "Welcome to %s" % self.sitename
        index.exposed = True
        
        def somewhere(self):
            return "Over the %s rainbow" % self.sitename
        somewhere.exposed = True
    
    
    cherrypy.root = Root()
    cherrypy.root.mydom2 = VHost("Domain 2")
    cherrypy.root.mydom3 = VHost("Domain 3")

    cherrypy.config.update({
            'server.logToScreen': False,
            'server.environment': 'production',
            'virtual_host_filter.on': True,
            'virtual_host_filter.www.mydom2.com': '/mydom2',
            'virtual_host_filter.www.mydom3.com': '/mydom3',
            'virtual_host_filter.www.mydom4.com': '/dom4',
    })

import helper

class VirtualHostFilterTest(helper.CPWebCase):
    
    def testVirtualHostFilter(self):
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
        
        # Test sub pages. See http://www.cherrypy.org/ticket/543.
        self.getPage("/somewhere", [('Host', 'www.mydom2.com')])
        self.assertBody('Over the Domain 2 rainbow')
        self.getPage("/somewhere", [('Host', 'www.mydom3.com')])
        self.assertBody('Over the Domain 3 rainbow')


if __name__ == "__main__":
    setup_server()
    helper.testmain()
