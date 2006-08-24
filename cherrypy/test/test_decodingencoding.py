from cherrypy.test import test
test.prefer_parent_path()

import cherrypy
europoundUnicode = u'\x80\xa3'
sing = u"\u6bdb\u6cfd\u4e1c: Sing, Little Birdie?"
sing8 = sing.encode('utf-8')
sing16 = sing.encode('utf-16')


def setup_server():
    class Root:
        def index(self, param):
            assert param == europoundUnicode
            yield europoundUnicode
        index.exposed = True
        
        def mao_zedong(self):
            return sing
        mao_zedong.exposed = True

    cherrypy.tree.mount(Root())
    cherrypy.config.update({
            'environment': 'test_suite',
            'tools.encode.on': True,
            'tools.decode.on': True,
    })


from cherrypy.test import helper


class DecodingEncodingTest(helper.CPWebCase):
    
    def testDecodingEncoding(self):
        europoundUtf8 = europoundUnicode.encode('utf-8')
        self.getPage('/?param=%s' % europoundUtf8)
        self.assertBody(europoundUtf8)
        
        # Default encoding should be utf-8
        self.getPage('/mao_zedong')
        self.assertBody(sing8)
        
        # Ask for utf-16.
        self.getPage('/mao_zedong', [('Accept-Charset', 'utf-16')])
        self.assertBody(sing16)
        
        # Ask for multiple encodings. ISO-8859-1 should fail, and utf-16
        # should be produced.
        self.getPage('/mao_zedong', [('Accept-Charset',
                                      'iso-8859-1;q=1, utf-16;q=0.5')])
        self.assertBody(sing16)
        
        # The "*" value should default to our default_encoding, utf-8
        self.getPage('/mao_zedong', [('Accept-Charset', '*;q=1, utf-7;q=.2')])
        self.assertBody(sing8)
        
        # Only allow iso-8859-1, which should fail and raise 406.
        self.getPage('/mao_zedong', [('Accept-Charset', 'iso-8859-1, *;q=0')])
        self.assertStatus("406 Not Acceptable")
        self.assertInBody("Your client sent this Accept-Charset header: "
                          "iso-8859-1, *;q=0. We tried these charsets: "
                          "iso-8859-1.")


if __name__ == "__main__":
    setup_server()
    helper.testmain()
