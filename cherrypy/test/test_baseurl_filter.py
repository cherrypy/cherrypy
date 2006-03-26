import test
test.prefer_parent_path()

import cherrypy


def setup_server():
    class Root:
        def index(self):
            raise cherrypy.HTTPRedirect('dummy')
        index.exposed = True
    
    cherrypy.tree.mount(Root())
    cherrypy.config.update({
            'server.environment': 'production',
            'server.log_to_screen': False,
            'base_url_filter.on': True,
            'base_url_filter.base_url': 'http://www.mydomain.com'
    })


import helper

class BaseUrlFilterTest(helper.CPWebCase):
    
    def testBaseUrlFilter(self):
        self.getPage("/")
        self.assertHeader('Location',
                          "http://www.mydomain.com%s/dummy" % self.prefix())


if __name__ == '__main__':
    setup_server()
    helper.testmain()
