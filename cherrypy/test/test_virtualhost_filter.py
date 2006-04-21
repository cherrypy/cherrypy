
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


    cherrypy.root = Root()
    cherrypy.root.mydom2 = VHost("Domain 2")
    cherrypy.root.mydom3 = VHost("Domain 3")

    cherrypy.config.update({
            'server.logToScreen': False,
            'server.environment': 'production',
            'tools.virtual_host.on': True,
            'tools.virtual_host.www.mydom2.com': '/mydom2',
            'tools.virtual_host.www.mydom3.com': '/mydom3',
            'tools.virtual_host.www.mydom4.com': '/dom4',
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


if __name__ == "__main__":
    setup_server()
    helper.testmain()
