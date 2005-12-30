import test
test.prefer_parent_path()

import sys

import cherrypy
import helper


class TutorialTest(helper.CPWebCase):
    
    def load_tut_module(self, tutorialName):
        """Import or reload tutorial module as needed."""
        cherrypy.config.reset()
        
        target = "cherrypy.tutorial." + tutorialName
        if target in sys.modules:
            module = reload(sys.modules[target])
        else:
            module = __import__(target, globals(), locals(), [''])
        
        cherrypy.config.update({'server.socket_host': self.HOST,
                                'server.socket_port': self.PORT,
                                'server.thread_pool': 10,
                                'server.log_to_screen': False,
                                'server.environment': "production",
                                })
    
    def test01HelloWorld(self):
        self.load_tut_module("tut01_helloworld")
        self.getPage("/")
        self.assertBody('Hello world!')
    
    def test02ExposeMethods(self):
        self.load_tut_module("tut02_expose_methods")
        self.getPage("/showMessage")
        self.assertBody('Hello world!')
    
    def test03GetAndPost(self):
        self.load_tut_module("tut03_get_and_post")
        
        # Try different GET queries
        self.getPage("/greetUser?name=Bob")
        self.assertBody("Hey Bob, what's up?")
        
        self.getPage("/greetUser")
        self.assertBody('Please enter your name <a href="./">here</a>.')
        
        self.getPage("/greetUser?name=")
        self.assertBody('No, really, enter your name <a href="./">here</a>.')
        
        # Try the same with POST
        self.getPage("/greetUser", method="POST", body="name=Bob")
        self.assertBody("Hey Bob, what's up?")
        
        self.getPage("/greetUser", method="POST", body="name=")
        self.assertBody('No, really, enter your name <a href="./">here</a>.')
    
    def test04ComplexSite(self):
        self.load_tut_module("tut04_complex_site")
        msg = '''
            <p>Here are some extra useful links:</p>
            
            <ul>
                <li><a href="http://del.icio.us">del.icio.us</a></li>
                <li><a href="http://www.mornography.de">Hendrik's weblog</a></li>
            </ul>
            
            <p>[<a href="../">Return to links page</a>]</p>'''
        self.getPage("/links/extra/")
        self.assertBody(msg)
    
    def test05DerivedObjects(self):
        self.load_tut_module("tut05_derived_objects")
        msg = '''
            <html>
            <head>
                <title>Another Page</title>
            <head>
            <body>
            <h2>Another Page</h2>
        
            <p>
            And this is the amazing second page!
            </p>
        
            </body>
            </html>
        '''
        self.getPage("/another/")
        self.assertBody(msg)
    
    def test06DefaultMethod(self):
        self.load_tut_module("tut06_default_method")
        self.getPage('/hendrik')
        self.assertBody('Hendrik Mans, CherryPy co-developer & crazy German '
                         '(<a href="./">back</a>)')
    def test07Sessions(self):
        self.load_tut_module("tut07_sessions")
        cherrypy.config.update({"session_filter.on": True})
        
        self.getPage('/')
        self.assertBody("\n            During your current session, you've viewed this"
                         "\n            page 1 times! Your life is a patio of fun!"
                         "\n        ")
        
        self.getPage('/', self.cookies)
        self.assertBody("\n            During your current session, you've viewed this"
                         "\n            page 2 times! Your life is a patio of fun!"
                         "\n        ")
    
    def test08GeneratorsAndYield(self):
        self.load_tut_module("tut08_generators_and_yield")
        self.getPage('/')
        self.assertBody('<html><body><h2>Generators rule!</h2>'
                         '<h3>List of users:</h3>'
                         'Remi<br/>Carlos<br/>Hendrik<br/>Lorenzo Lamas<br/>'
                         '</body></html>')
    
    def test09Files(self):
        self.load_tut_module("tut09_files")
        
        # Test upload
        h = [("Content-type", "multipart/form-data; boundary=x"),
             ("Content-Length", "110")]
        b = """--x
Content-Disposition: form-data; name="myFile"; filename="hello.txt"
Content-Type: text/plain

hello
--x--
"""
        self.getPage('/upload', h, "POST", b)
        self.assertBody('''<html>
        <body>
            myFile length: 5<br />
            myFile filename: hello.txt<br />
            myFile mime-type: text/plain
        </body>
        </html>''')
    
        # Test download
        self.getPage('/download')
        self.assertStatus("200 OK")
        self.assertHeader("Content-Type", "application/x-download")
        self.assertHeader("Content-Disposition", "attachment; filename=pdf_file.pdf")
        self.assertEqual(len(self.body), 85698)
    
    def test10HTTPErrors(self):
        self.load_tut_module("tut10_http_errors")
        
        self.getPage("/")
        self.assertInBody("""<a href="toggleTracebacks">""")
        self.assertInBody("""<a href="/doesNotExist">""")
        self.assertInBody("""<a href="/error?code=403">""")
        self.assertInBody("""<a href="/error?code=500">""")
        self.assertInBody("""<a href="/messageArg">""")
        
        tracebacks = cherrypy.config.get('server.show_tracebacks')
        self.getPage("/toggleTracebacks")
        self.assertEqual(cherrypy.config.get('server.show_tracebacks'), not tracebacks)
        self.assertStatus("302 Found")
        
        self.getPage("/error?code=500")
        self.assertStatus("500 Internal error")
        self.assertInBody("The server encountered an unexpected condition "
                          "which prevented it from fulfilling the request.")
        
        self.getPage("/error?code=403")
        self.assertStatus("403 Forbidden")
        self.assertInBody("<h2>You can't do that!</h2>")
        
        self.getPage("/messageArg")
        self.assertStatus("500 Internal error")
        self.assertInBody("If you construct an HTTPError with a 'message'")


if __name__ == "__main__":
    helper.testmain()
