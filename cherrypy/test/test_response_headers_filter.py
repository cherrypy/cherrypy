import test
test.prefer_parent_path()

import cherrypy
from cherrypy._cputil import headers

class Root:
    @headers([("Content-Language", "en-GB"),
              ('Content-Type', 'text/plain')])
    def index(self):
        yield "Hello, world"
    index.exposed = True

    def other(self):
        return "salut"
    other.exposed = True
    
cherrypy.root = Root()

import helper

class ResponseHeadersFilterTest(helper.CPWebCase):

    def testResponseHeadersDecorator(self):
        self.getPage('/')
        self.assertHeader("Content-Language", "en-GB")
        self.assertHeader('Content-Type', 'text/plain')

    def testResponseHeadersFilter(self):
        cherrypy.config.update({'/other': {
            'response_headers_filter.on': True,
            'response_headers_filter.headers': [("Content-Language", "fr"),
                                                ('Content-Type', 'text/plain')]
        }})
        self.getPage('/other')
        self.assertHeader("Content-Language", "fr")
        # the filter should only change headers that have not been set yet
        # Content-Type should have been set when the response object
        # was created (default to text/html)
        self.assertHeader('Content-Type', 'text/html')

if __name__ == "__main__":
    helper.testmain()
