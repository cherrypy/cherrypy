"""
Copyright (c) 2004, CherryPy Team (team@cherrypy.org)
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
    * Neither the name of the CherryPy Team nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

# TODO: Have a real object mapping test once the object mapping -> URI
#   algorithm is finalized

import helper

code = """
from cherrypy import cpg
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
    def notExposed(self):
        return "not exposed"
class Dir1:
    def index(self):
        return "index for dir1"
    index.exposed = True
    def default(self, *params):
        return repr(params)
    default.exposed = True
class Dir2:
    def index(self):
        return "index for dir2, path is:" + cpg.request.path
    index.exposed = True
    def method(self):
        return "method for dir2"
    method.exposed = True
cpg.root = Root()
cpg.root.dir1 = Dir1()
cpg.root.dir1.dir2 = Dir2()
cpg.server.start(configFile = 'testsite.cfg')
"""
config = ""
testList = [
    ("", "world"),
    ("/this/method/does/not/exist", "default:('this', 'method', 'does', 'not', 'exist')"),
    ("/other", "other"),
    ("/notExposed", "default:('notExposed',)"),
    ("/dir1/dir2/", "index for dir2, path is:/dir1/dir2/"),
]
urlList = [test[0] for test in testList]
expectedResultList = [test[1] for test in testList]

def test(infoMap, failedList, skippedList):
    print "    Testing object mapping...",
    helper.checkPageResult('Object mapping', infoMap, code, config, urlList, expectedResultList, failedList)
