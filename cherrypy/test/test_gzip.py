from cherrypy import test
test.prefer_parent_path()

import gzip, StringIO
import cherrypy

def setup_server():
    class Root:
        def index(self):
            yield "Hello, world"
        index.exposed = True
        
        def noshow(self):
            # Test for ticket #147, where yield showed no exceptions (content-
            # encoding was still gzip even though traceback wasn't zipped).
            raise IndexError()
            yield "Here be dragons"
        noshow.exposed = True
        
        def noshow_stream(self):
            # Test for ticket #147, where yield showed no exceptions (content-
            # encoding was still gzip even though traceback wasn't zipped).
            raise IndexError()
            yield "Here be dragons"
        noshow_stream.exposed = True
        noshow_stream._cp_config = {'stream_response': True}
    
    cherrypy.tree.mount(Root())
    cherrypy.config.update({
        'global': {'log_to_screen': False,
                   'environment': 'production',
                   'show_tracebacks': True,
                   'tools.gzip.on': True,
                   },
    })


from cherrypy.test import helper

europoundUtf8 = u'\x80\xa3'.encode('utf-8')

class GzipTest(helper.CPWebCase):
    
    def testGzip(self):
        zbuf = StringIO.StringIO()
        zfile = gzip.GzipFile(mode='wb', fileobj=zbuf, compresslevel=9)
        zfile.write("Hello, world")
        zfile.close()
        
        self.getPage('/', headers=[("Accept-Encoding", "gzip")])
        self.assertInBody(zbuf.getvalue()[:3])
        self.assertHeader("Vary", "Accept-Encoding")
        
        # Test when gzip is denied.
        self.getPage('/', headers=[("Accept-Encoding", "identity")])
        self.assertNoHeader("Vary")
        self.assertBody("Hello, world")
        
        self.getPage('/', headers=[("Accept-Encoding", "gzip;q=0")])
        self.assertNoHeader("Vary")
        self.assertBody("Hello, world")
        
        self.getPage('/', headers=[("Accept-Encoding", "*;q=0")])
        self.assertStatus(406)
        self.assertNoHeader("Vary")
        self.assertErrorPage(406, "identity, gzip")
        
        # Test for ticket #147
        self.getPage('/noshow', headers=[("Accept-Encoding", "gzip")])
        self.assertNoHeader('Content-Encoding')
        self.assertStatus(500)
        self.assertErrorPage(500, pattern="IndexError\n")
        
        # In this case, there's nothing we can do to deliver a
        # readable page, since 1) the gzip header is already set,
        # and 2) we may have already written some of the body.
        # The fix is to never stream yields when using gzip.
        self.getPage('/noshow_stream',
                     headers=[("Accept-Encoding", "gzip")])
        self.assertHeader('Content-Encoding', 'gzip')
        self.assertMatchesBody(r"Unrecoverable error in the server.$")


if __name__ == "__main__":
    setup_server()
    helper.testmain()
