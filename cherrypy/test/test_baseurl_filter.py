import cherrypy


class Root:
    def index(self):
        raise cherrypy.HTTPRedirect('dummy')
    index.exposed = True

cherrypy.root = Root()
cherrypy.config.update({
        'server.environment': 'production',
        'server.logToScreen': False,
        'baseUrlFilter.on': True,
        'baseUrlFilter.baseUrl': 'http://www.mydomain.com'
})

import helper

class BaseUrlFilterTest(helper.CPWebCase):
    
    def testBaseUrlFilter(self):
        self.getPage("/")
        self.assertHeader('Location',
                          "http://www.mydomain.com%s/dummy" % helper.vroot)


if __name__ == '__main__':
    helper.testmain()

