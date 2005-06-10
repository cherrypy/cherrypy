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
import helper
import sys
from cherrypy import cpg


def load_tut_module(tutorialName):
    """Import or reload tutorial module as needed."""
    target = "cherrypy.tutorial." + tutorialName
    if target in sys.modules:
        module = reload(sys.modules[target])
    else:
        module = __import__(target)


class TutorialTest(unittest.TestCase):
    
    def test01HelloWorld(self):
        load_tut_module("tut01_helloworld")
        cpg.server.start(initOnly=True)
        helper.request("/")
        self.assertEqual(cpg.response.body, 'Hello world!')
    
    def test02ExposeMethods(self):
        load_tut_module("tut02_expose_methods")
        cpg.server.start(initOnly=True)
        helper.request("/showMessage")
        self.assertEqual(cpg.response.body, 'Hello world!')
    
    def test03GetAndPost(self):
        load_tut_module("tut03_get_and_post")
        cpg.server.start(initOnly=True)
        
        helper.request("/greetUser?name=Bob")
        self.assertEqual(cpg.response.body, "Hey Bob, what's up?")
        
        helper.request("/greetUser")
        self.assertEqual(cpg.response.body,
                         'Please enter your name <a href="./">here</a>.')
        
        helper.request("/greetUser?name=")
        self.assertEqual(cpg.response.body,
                         'No, really, enter your name <a href="./">here</a>.')
    
    def test04ComplexSite(self):
        load_tut_module("tut04_complex_site")
        cpg.server.start(initOnly=True)
        msg = '''
            <p>Here are some extra useful links:</p>
            
            <ul>
                <li><a href="http://del.icio.us">del.icio.us</a></li>
                <li><a href="http://www.mornography.de">Hendrik's weblog</a></li>
            </ul>
            
            <p>[<a href="../">Return to links page</a>]</p>'''
        helper.request("/links/extra/")
        self.assertEqual(cpg.response.body, msg)
    
    def test05DerivedObjects(self):
        load_tut_module("tut05_derived_objects")
        cpg.server.start(initOnly=True)
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
        helper.request("/another/")
        self.assertEqual(cpg.response.body, msg)
    
    def test06Aspects(self):
        load_tut_module("tut06_aspects")
        cpg.server.start(initOnly=True)
        msg = '''
            <html>
            <head>
                <title>Tutorial 6 -- Aspect Powered!</title>
            <head>
            <body>
            <h2>Tutorial 6 -- Aspect Powered!</h2>
        
            <p>
            Isn't this exciting? There's
            <a href="./another/">another page</a>, too!
            </p>
        
            </body>
            </html>
        '''
        helper.request("/")
        self.assertEqual(cpg.response.body, msg)
    
    def test07DefaultMethod(self):
        load_tut_module("tut07_default_method")
        cpg.server.start(initOnly=True)
        helper.request('/hendrik')
        self.assertEqual(cpg.response.body,
                         'Hendrik Mans, CherryPy co-developer & crazy German '
                         '(<a href="./">back</a>)')
    
    def test08Sessions(self):
        load_tut_module("tut08_sessions")
        cpg.server.start(initOnly=True)
        
        cpg.config.configMap["/"] = {'session.storageType': 'ram',
                                     'session.cookieName': 'CherryPySession',
                                     'session.timeout': 60,
                                     'session.cleanUpDelay': 60,
                                     'session.storageFileDir': '',
                                     }
        
        helper.request('/')
        self.assertEqual(cpg.response.body,
                         "\n            During your current session, you've viewed this"
                         "\n            page 1 times! Your life is a patio of fun!"
                         "\n        ")
        
        helper.request('/', [('Cookie', dict(cpg.response.headers)['Set-Cookie'])])
        self.assertEqual(cpg.response.body,
                         "\n            During your current session, you've viewed this"
                         "\n            page 2 times! Your life is a patio of fun!"
                         "\n        ")
    
    def test09GeneratorsAndYield(self):
        load_tut_module("tut09_generators_and_yield")
        cpg.server.start(initOnly=True)
        helper.request('/')
        self.assertEqual(cpg.response.body,
                         '<html><body><h2>Generators rule!</h2>'
                         '<h3>List of users:</h3>'
                         'Remi<br/>Carlos<br/>Hendrik<br/>Lorenzo Lamas<br/>'
                         '</body></html>')


if __name__ == "__main__":
    unittest.main()

