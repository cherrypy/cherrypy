from cherrypy.test import test
test.prefer_parent_path()

import os
localDir = os.path.join(os.getcwd(), os.path.dirname(__file__))
tidy_path = os.path.join(localDir, "tidy")

import cherrypy
from cherrypy import tools

doctype = ('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" '
           '"http://www.w3.org/TR/xhtml1/DTD/strict.dtd">')

def setup_server():
    class Root:
        _cp_config = {
            'tools.tidy.on': True,
            'tools.tidy.tidy_path': tidy_path,
            'tools.tidy.temp_dir': localDir,
            }
        
        def plaintext(self):
            yield "Hello, world"
        plaintext.exposed = True
        plaintext._cp_config = {'tools.tidy.warnings': False}
        
        def validhtml(self):
            return "<html><body><h1>This should be valid</h1></body></html>"
        validhtml.exposed = True
        validhtml._cp_config = {'tools.tidy.warnings': False}
        
        def warning(self, skip_doctype=False):
            if skip_doctype:
                # This should raise a warning
                pass
            else:
                yield doctype
            
            yield "<html><head><title>Meh</title></head>"
            yield "<body>Normal body</body></html>"
        warning.exposed = True
    
    cherrypy.config.update({'environment': 'test_suite'})
    cherrypy.tree.mount(Root())


from cherrypy.test import helper

class TidyTest(helper.CPWebCase):

    def test_Tidy_Tool(self):
        if not os.path.exists(tidy_path) and not os.path.exists(tidy_path + ".exe"):
            print "skipped (tidy not found) ",
            return
        
        self.getPage('/validhtml')
        self.assertStatus(200)
        self.assertBody("<html><body><h1>This should be valid</h1></body></html>")
        
        self.getPage('/plaintext')
        self.assertStatus(200)
        self.assertBody('Hello, world')
        
        self.getPage('/warning')
        self.assertStatus(200)
        self.assertBody(doctype + "<html><head><title>Meh</title></head>"
                        "<body>Normal body</body></html>")
        
        self.getPage('/warning?skip_doctype=YES')
        self.assertStatus(200)
        self.assertInBody("Wrong HTML")



if __name__ == "__main__":
    setup_server()
    helper.testmain()
