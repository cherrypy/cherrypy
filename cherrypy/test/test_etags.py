import test
test.prefer_parent_path()

import cherrypy
from cherrypy.lib import cptools


def setup_server():
    class Root:
        def resource(self):
            return "Oh wah ta goo Siam."
        resource.exposed = True
    
    conf = {
        '/resource': {
            'tools.etags.on': True,
            'tools.etags.autotags': True,
        },
        }
    cherrypy.tree.mount(Root(), conf=conf)
    
    cherrypy.config.update({
        'log_to_screen': False,
        'environment': 'production',
        'show_tracebacks': True,
        })

import helper

class ETagTest(helper.CPWebCase):
    
    def testETags(self):
        self.getPage("/resource")
        self.assertStatus('200 OK')
        self.assertHeader('Content-Type', 'text/html')
        self.assertBody('Oh wah ta goo Siam.')
        self.assertHeader('ETag')
        for k, v in self.headers:
            if k.lower() == 'etag':
                etag = v
                break
        
        # Test If-Match (both valid and invalid)
        self.getPage("/resource", headers=[('If-Match', etag)])
        self.assertStatus("200 OK")
        self.getPage("/resource", headers=[('If-Match', "*")])
        self.assertStatus("200 OK")
        self.getPage("/resource", headers=[('If-Match', "a bogus tag")])
        self.assertStatus("412 Precondition Failed")
        
        # Test If-None-Match (both valid and invalid)
        self.getPage("/resource", headers=[('If-None-Match', etag)])
        self.assertStatus("304 Not modified")
        self.getPage("/resource", method='POST', headers=[('If-None-Match', etag)])
        self.assertStatus("412 Precondition Failed")
        self.getPage("/resource", headers=[('If-None-Match', "*")])
        self.assertStatus("304 Not modified")
        self.getPage("/resource", headers=[('If-None-Match', "a bogus tag")])
        self.assertStatus("200 OK")

if __name__ == "__main__":
    setup_server()
    helper.testmain()
