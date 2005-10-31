
import cherrypy
europoundUnicode = u'\x80\xa3'

class Root:
    def index(self, param):
        assert param == europoundUnicode
        yield europoundUnicode
    index.exposed = True

cherrypy.root = Root()
cherrypy.config.update({
        'server.logToScreen': False,
        'server.environment': 'production',
        'encodingFilter.on': True,
        'decodingFilter.on': True
})


import helper

europoundUtf8 = europoundUnicode.encode('utf-8')

class DecodingEncodingFilterTest(helper.CPWebCase):
    
    def testDecodingEncodingFilter(self):
        self.getPage('/?param=%s' % europoundUtf8)
        self.assertBody(europoundUtf8)


if __name__ == "__main__":
    helper.testmain()
