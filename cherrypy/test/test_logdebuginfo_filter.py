import test
test.prefer_parent_path()

import cherrypy


def setup_server():
    class Root:
        def index(self):
            yield "Hello, world"
        index.exposed = True

        def bug326(self, file):
            return "OK"
        bug326.exposed = True

    cherrypy.root = Root()

    cherrypy.config.update({
        'server.log_to_screen': False,
        'server.environment': 'production',
        'log_debug_info_filter.on': True,
        '/bug326': {
            'server.max_request_body_size': 300,
            'server.environment': 'development',
        }
    })



import helper

class LogDebugInfoFilterTest(helper.CPWebCase):
    
    def testLogDebugInfoFilter(self):
        self.getPage('/')
        self.assertInBody('Build time')
        self.assertInBody('Page size')
        # not compatible with the session_filter
        #self.assertInBody('Session data size')

    def testBug326(self):
        b = """--x
Content-Disposition: form-data; name="file"; filename="hello.txt"
Content-Type: text/plain

%s
--x--
""" % ("x" * 300)
        h = [("Content-type", "multipart/form-data; boundary=x"),
             ("Content-Length", len(b))]
        self.getPage('/bug326', h, "POST", b)
        self.assertStatus("413 Request Entity Too Large")


if __name__ == "__main__":
    setup_server()
    helper.testmain()
