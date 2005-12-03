import test
test.prefer_parent_path()

import gzip, StringIO
import cherrypy

europoundUnicode = u'\x80\xa3'

class Root:
    def index(self):
        yield u"Hello,"
        yield u"world"
        yield europoundUnicode
    index.exposed = True

cherrypy.root = Root()
cherrypy.config.update({
        'server.log_to_screen': False,
        'server.environment': 'production',
        'gzip_filter.on': True,
        'encoding_filter.on': True,
})

import helper

class CombinedFiltersTest(helper.CPWebCase):
    
    def testCombinedFilters(self):
        expectedResult = (u"Hello,world" + europoundUnicode).encode('utf-8')
        zbuf = StringIO.StringIO()
        zfile = gzip.GzipFile(mode='wb', fileobj=zbuf, compresslevel=9)
        zfile.write(expectedResult)
        zfile.close()
        
        self.getPage("/", headers=[("Accept-Encoding", "gzip")])
        self.assertInBody(zbuf.getvalue()[:3])


if __name__ == '__main__':
    helper.testmain()
