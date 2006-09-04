from cherrypy.test import test
test.prefer_parent_path()

import cherrypy
from cherrypy import tools


def setup_server():
    class Root:
        def index(self):
            yield "Hello, world"
        index.exposed = True
        h = [("Content-Language", "en-GB"), ('Content-Type', 'text/plain')]
        tools.response_headers(headers=h)(index)
        
        def other(self):
            return "salut"
        other.exposed = True
        other._cp_config = {
            'tools.response_headers.on': True,
            'tools.response_headers.headers': [("Content-Language", "fr"),
                                               ('Content-Type', 'text/plain')],
            }
    
    class Referer:
        def accept(self):
            return "Accepted!"
        accept.exposed = True
        reject = accept
    
    conf = {'/referer': {'tools.referer.on': True,
                         'tools.referer.pattern': r'http://[^/]*thisdomain\.com',
                         },
            '/referer/reject': {'tools.referer.accept': False,
                                'tools.referer.accept_missing': True,
                                },
            }
    
    root = Root()
    root.referer = Referer()
    cherrypy.tree.mount(root, config=conf)
    cherrypy.config.update({'environment': 'test_suite'})


from cherrypy.test import helper

class ResponseHeadersTest(helper.CPWebCase):

    def testResponseHeadersDecorator(self):
        self.getPage('/')
        self.assertHeader("Content-Language", "en-GB")
        self.assertHeader('Content-Type', 'text/plain')

    def testResponseHeaders(self):
        self.getPage('/other')
        self.assertHeader("Content-Language", "fr")
        self.assertHeader('Content-Type', 'text/plain')


class RefererTest(helper.CPWebCase):
    
    def testReferer(self):
        self.getPage('/referer/accept')
        self.assertErrorPage(403, 'Forbidden Referer header.')
        
        self.getPage('/referer/accept',
                     headers=[('Referer', 'http://www.thisdomain.com/')])
        self.assertStatus(200)
        self.assertBody('Accepted!')
        
        # Reject
        self.getPage('/referer/reject')
        self.assertStatus(200)
        self.assertBody('Accepted!')
        
        self.getPage('/referer/reject',
                     headers=[('Referer', 'http://www.thisdomain.com/')])
        self.assertErrorPage(403, 'Forbidden Referer header.')


if __name__ == "__main__":
    setup_server()
    helper.testmain()
