import test
test.prefer_parent_path()

import gzip, StringIO
import cherrypy

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

cherrypy.root = Root()
cherrypy.config.update({
    'global': {'server.log_to_screen': False,
               'server.environment': 'production',
               'server.show_tracebacks': True,
               'gzip_filter.on': True,
               },
    '/noshow_stream': {'stream_response': True},
})


import helper

europoundUtf8 = u'\x80\xa3'.encode('utf-8')

class GzipFilterTest(helper.CPWebCase):
    
    def testGzipFilter(self):
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
        self.assertStatus("406 Not Acceptable")
        self.assertNoHeader("Vary")
        self.assertErrorPage(406, "identity, gzip")
        
        # Test for ticket #147
        helper.webtest.ignored_exceptions.append(IndexError)
        try:
            self.getPage('/noshow', headers=[("Accept-Encoding", "gzip")])
            self.assertNoHeader('Content-Encoding')
            self.assertStatus('500 Internal error')
            self.assertErrorPage(500, pattern="IndexError\n")
            
            # In this case, there's nothing we can do to deliver a
            # readable page, since 1) the gzip header is already set,
            # and 2) we may have already written some of the body.
            # The fix is to never stream yields when using gzip.
            if cherrypy.server.httpserver is None:
                self.assertRaises(IndexError, self.getPage,
                                  '/noshow_stream',
                                  [("Accept-Encoding", "gzip")])
            else:
                self.getPage('/noshow_stream',
                             headers=[("Accept-Encoding", "gzip")])
                self.assertHeader('Content-Encoding', 'gzip')
                self.assertMatchesBody(r"Unrecoverable error in the server.$")
        finally:
            helper.webtest.ignored_exceptions.pop()


if __name__ == "__main__":
    helper.testmain()
