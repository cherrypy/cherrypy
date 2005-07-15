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

import cherrypy
from cherrypy.lib import httptools

class Root:
    def index(self, name="world"):
        return name
    index.exposed = True
    
    def default(self, *params):
        return "default:"+repr(params)
    default.exposed = True
    
    def other(self):
        return "other"
    other.exposed = True
    
    def extra(self, *p):
        return repr(p)
    extra.exposed = True
    
    def redirect(self):
        return httptools.redirect('dir1/')
    redirect.exposed = True
    
    def notExposed(self):
        return "not exposed"


class Dir1:
    def index(self):
        return "index for dir1"
    index.exposed = True
    
    def myMethod(self):
        return "myMethod from dir1, object Path is:" + repr(cherrypy.request.objectPath)
    myMethod.exposed = True
    
    def default(self, *params):
        return "default for dir1, param is:" + repr(params)
    default.exposed = True


class Dir2:
    def index(self):
        return "index for dir2, path is:" + cherrypy.request.path
    index.exposed = True
    
    def method(self):
        return "method for dir2"
    method.exposed = True


class Dir3:
    def default(self):
        return "default for dir3, not exposed"


class Dir4:
    def index(self):
        return "index for dir4, not exposed"

cherrypy.root = Root()
cherrypy.root.dir1 = Dir1()
cherrypy.root.dir1.dir2 = Dir2()
cherrypy.root.dir1.dir2.dir3 = Dir3()
cherrypy.root.dir1.dir2.dir3.dir4 = Dir4()
cherrypy.config.update({
    'global': {
        'server.logToScreen': False,
        'server.environment': "production",
    }
})
cherrypy.server.start(initOnly=True)


import unittest
import helper

class ObjectMappingTest(helper.CPWebCase):
    
    def testObjectMapping(self):
        self.getPage('/')
        self.assertBody('world')
        
        self.getPage("/dir1/myMethod")
        self.assertBody("myMethod from dir1, object Path is:'/dir1/myMethod'")
        
        self.getPage("/this/method/does/not/exist")
        self.assertBody("default:('this', 'method', 'does', 'not', 'exist')")
        
        self.getPage("/extra/too/much")
        self.assertBody("default:('extra', 'too', 'much')")
        
        self.getPage("/other")
        self.assertBody('other')
        
        self.getPage("/notExposed")
        self.assertBody("default:('notExposed',)")
        
        self.getPage("/dir1/dir2/")
        self.assertBody('index for dir2, path is:/dir1/dir2/')
        
        self.getPage("/dir1/dir2")
        self.assert_(self.status in ('302 Found', '303 See Other'))
        self.assertHeader('Location', 'http://%s:%s/dir1/dir2/'
                          % (helper.HOST, helper.PORT))
        
        self.getPage("/dir1/dir2/dir3/dir4/index")
        self.assertBody("default for dir1, param is:('dir2', 'dir3', 'dir4', 'index')")
        
        self.getPage("/redirect")
        self.assertStatus('302 Found')
        self.assertHeader('Location', 'http://%s:%s/dir1/'
                          % (helper.HOST, helper.PORT))


if __name__ == "__main__":
    unittest.main()

