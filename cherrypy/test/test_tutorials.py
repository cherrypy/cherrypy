"""
Copyright (c) 2004, CherryPy Team (team@cherrypy.org)
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, 
are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice, 
      this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice, 
      this list of conditions and the following disclaimer in the documentation 
      and/or other materials provided with the distribution.
    * Neither the name of the CherryPy Team nor the names of its contributors 
      may be used to endorse or promote products derived from this software 
      without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND 
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED 
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE 
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE 
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL 
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR 
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER 
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, 
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE 
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import unittest
import sys

import cherrypy
from cherrypy.test import helper


class TutorialTest(helper.CPWebCase):
    
    def load_tut_module(self, tutorialName):
        """Import or reload tutorial module as needed."""
        cherrypy.config.reset()
        cherrypy.config.update({'server.socketHost': self.HOST,
                                'server.socketPort': self.PORT,
                                'server.threadPool': 10,
                                'server.logToScreen': False,
                                'server.environment': "production",
                                })
        
        target = "cherrypy.tutorial." + tutorialName
        if target in sys.modules:
            module = reload(sys.modules[target])
        else:
            module = __import__(target, globals(), locals(), [''])
        
        cherrypy.server.start(initOnly=True)
    
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
        cherrypy.config.update({"sessionFilter.on": True})
        
        self.getPage('/')
        self.assertBody("\n            During your current session, you've viewed this"
                         "\n            page 1 times! Your life is a patio of fun!"
                         "\n        ")
        
        self.getPage('/', self.cookies)
        self.assertBody("\n            During your current session, you've viewed this"
                         "\n            page 2 times! Your life is a patio of fun!"
                         "\n        ")
    
    def test08AdvancedSessions(self):
        self.load_tut_module("tut08_advanced_sessions")
        cherrypy.config.update({"sessionFilter.on": True})
        
        self.getPage('/')
        self.assertInBody("viewed this page 1 times")
        
        self.getPage('/', self.cookies)
        self.assertInBody("viewed this page 2 times")
    
    def test09GeneratorsAndYield(self):
        self.load_tut_module("tut09_generators_and_yield")
        self.getPage('/')
        self.assertBody('<html><body><h2>Generators rule!</h2>'
                         '<h3>List of users:</h3>'
                         'Remi<br/>Carlos<br/>Hendrik<br/>Lorenzo Lamas<br/>'
                         '</body></html>')
    
    def test10FileUpload(self):
        self.load_tut_module("tut10_file_upload")
        
        h = [("Content-type", "multipart/form-data; boundary=x"),
             ("Content-Length", "110")]
        b = """--x
Content-Disposition: form-data; name="myFile"; filename="hello.txt"
Content-Type: text/plain

hello
--x--
"""
        self.getPage('/upload', h, "POST", b)
        self.assertBody('''
        <html><body>
            myFile length: 5<br />
            myFile filename: hello.txt<br />
            myFile mime-type: text/plain
        </body></html>
        ''')

if __name__ == "__main__":
    helper.testmain()
