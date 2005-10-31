import cherrypy

class Root:
    def index(self):
        yield "Hello, world"
    index.exposed = True

    def bug326(self, file):
        return "OK"
    bug326.exposed = True

cherrypy.root = Root()

cherrypy.config.update({
        'session.storageType': 'ram',
        'session.timeout': 60,
        'session.cleanUpDelay': 60,
        'session.cookieName': 'CherryPySession',
        'session.storageFileDir': '',
        
        'server.logToScreen': False,
        'server.environment': 'production',
        'logDebugInfoFilter.on': True,
})



import helper

class LogDebugInfoFilterTest(helper.CPWebCase):
    
    def testLogDebugInfoFilter(self):
        self.getPage('/')
        self.assertInBody('Build time')
        self.assertInBody('Page size')
        # not compatible with the sessionFilter
        #self.assertInBody('Session data size')

    def testBug326(self):
        httpcls = cherrypy.server.httpserverclass
        if httpcls and httpcls.__name__ == "WSGIServer":
            h = [("Content-type", "multipart/form-data; boundary=x"),
                 ("Content-Length", "110")]
            b = """--x
Content-Disposition: form-data; name="file"; filename="hello.txt"
Content-Type: text/plain

hello
--x--
"""
            cherrypy.config.update({
                ('%s/bug326' % helper.vroot): {
                    'server.maxRequestBodySize': 3,
                    'server.environment': 'development',
                }
            })
            ignore = helper.webtest.ignored_exceptions
            ignore.append(AttributeError)
            try:
                self.getPage('/bug326', h, "POST", b)
                self.assertStatus("413 Request Entity Too Large")
            finally:
                ignore.pop()

if __name__ == "__main__":
    helper.testmain()
