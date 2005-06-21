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

from cherrypy import cpg
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
        return "myMethod from dir1, object Path is:" + repr(cpg.request.objectPath)
    myMethod.exposed = True
    
    def default(self, *params):
        return "default for dir1, param is:" + repr(params)
    default.exposed = True


class Dir2:
    def index(self):
        return "index for dir2, path is:" + cpg.request.path
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

cpg.root = Root()
cpg.root.dir1 = Dir1()
cpg.root.dir1.dir2 = Dir2()
cpg.root.dir1.dir2.dir3 = Dir3()
cpg.root.dir1.dir2.dir3.dir4 = Dir4()
cpg.config.update({
    'global': {
        'server.logToScreen': False,
        'server.environment': "production",
    }
})
cpg.server.start(initOnly=True)

import unittest
import helper

class ObjectMappingTest(unittest.TestCase):
    
    def testObjectMapping(self):
        helper.request('/')
        self.assertEqual(cpg.response.body, 'world')
        
        helper.request("/dir1/myMethod")
        self.assertEqual(cpg.response.body, "myMethod from dir1, object Path is:'/dir1/myMethod'")
        
        helper.request("/this/method/does/not/exist")
        self.assertEqual(cpg.response.body, "default:('this', 'method', 'does', 'not', 'exist')")
        
        helper.request("/extra/too/much")
        self.assertEqual(cpg.response.body, "default:('extra', 'too', 'much')")
        
        helper.request("/other")
        self.assertEqual(cpg.response.body, 'other')
        
        helper.request("/notExposed")
        self.assertEqual(cpg.response.body, "default:('notExposed',)")
        
        helper.request("/dir1/dir2/")
        self.assertEqual(cpg.response.body, 'index for dir2, path is:/dir1/dir2/')
        
        helper.request("/dir1/dir2")
        self.assert_(cpg.response.status in ('302 Found', '303 See Other'))
        self.assertEqual(cpg.response.headerMap['Location'],
                         'http://%s:%s/dir1/dir2/' % (helper.HOST, helper.PORT))
        
        helper.request("/dir1/dir2/dir3/dir4/index")
        self.assertEqual(cpg.response.body,
                         "default for dir1, param is:('dir2', 'dir3', 'dir4', 'index')")
        
        helper.request("/redirect")
        self.assertEqual(cpg.response.status, '302 Found')
        self.assertEqual(cpg.response.headerMap['Location'],
                         'http://%s:%s/dir1/' % (helper.HOST, helper.PORT))


if __name__ == "__main__":
    unittest.main()

