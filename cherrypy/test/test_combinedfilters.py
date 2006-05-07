import test
test.prefer_parent_path()

import gzip, StringIO
import cherrypy

europoundUnicode = u'\x80\xa3'

def setup_server():
    class Root:
        def index(self):
            yield u"Hello,"
            yield u"world"
            yield europoundUnicode
        index.exposed = True

    cherrypy.tree.mount(Root())
    cherrypy.config.update({
            'log_to_screen': False,
            'environment': 'production',
            'tools.gzip.on': True,
            'tools.encode.on': True,
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
    setup_server()
    helper.testmain()
