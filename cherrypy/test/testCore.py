"""
Copyright (c) 2005, CherryPy Team (team@cherrypy.org)
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

"""Basic tests for the CherryPy core: request handling."""

import helper

code = """
from cherrypy import cpg

class Root:
    def index(self):
        return "hello"
    index.exposed = True
cpg.root = Root()


import types
class TestType(type):
    def __init__(cls, name, bases, dct):
        type.__init__(name, bases, dct)
        for value in dct.itervalues():
            if type(value) == types.FunctionType:
                value.exposed = True
        setattr(cpg.root, name.lower(), cls())
class Test(object):
    __metaclass__ = TestType


class Status(Test):
    
    def index(self):
        return "normal"
    
    def blank(self):
        cpg.response.status = ""
    
    # According to RFC 2616, new status codes are OK as long as they
    # are between 100 and 599.
    
    # Here is an illegal code...
    def illegal(self):
        cpg.response.status = 781
        return "oops"
    
    # ...and here is an unknown but legal code.
    def unknown(self):
        cpg.response.status = "431 My custom error"
        return "funky"
    
    # Non-numeric code
    def bad(self):
        cpg.response.status = "error"
        return "hello"

class Redirect(Test):
    
    def index(self):
        return "child"

class Flatten(Test):
    
    def as_string(self):
        return "content"
    
    def as_list(self):
        return ["con", "tent"]
    
    def as_yield(self):
        yield "content"
    
    def as_dblyield(self):
        yield self.as_yield()
    
    def as_refyield(self):
        for chunk in self.as_yield():
            yield chunk

class Error(Test):
    
    def page_method(self):
        raise ValueError
    
    def page_yield(self):
        yield "hello"
        raise ValueError
    
    def page_http_1_1(self):
        cpg.response.headerMap["Content-Length"] = 39
        def inner():
            yield "hello"
            raise ValueError
            yield "oops"
        return inner()

cpg.config.update({
    '/': {
        'server.socketPort': 8000,
        'server.environment': 'production',
    }
})
cpg.server.start()
"""

testList = [
    ("/status/", "cpg.response.body == 'normal' and cpg.response.status == '200 OK'"),
    ("/status/blank", "cpg.response.body == '' and cpg.response.status == '200 OK'"),
    ("/status/illegal", "cpg.response.body == 'oops' and cpg.response.status == '500 Internal error'"),
    ("/status/unknown", "cpg.response.body == 'funky' and cpg.response.status == '431 My custom error'"),
    ("/status/bad", "cpg.response.body == 'hello' and cpg.response.status == '500 Internal error'"),

    ("/redirect/", "cpg.response.body == 'child' and cpg.response.status == '200 OK'"),
    ("/redirect", "cpg.response.body == '' and cpg.response.status == '302 Found'"),

    ("/flatten/as_string", "cpg.response.body == 'content'"),
    ("/flatten/as_list", "cpg.response.body == 'content'"),
    ("/flatten/as_yield", "cpg.response.body == 'content'"),
    ("/flatten/as_dblyield", "cpg.response.body == 'content'"),
    ("/flatten/as_refyield", "cpg.response.body == 'content'"),

    ("/error/page_method", r"cpg.response.body.endswith(' in page_method\n    raise ValueError\nValueError\n')"),
    ("/error/page_yield", r"cpg.response.body.endswith(' in page_yield\n    raise ValueError\nValueError\n')"),
    ("/error/page_http_1_1", r"cpg.response.body == 'helloUnrecoverable error in the server.'"),
]

def test(infoMap, failedList, skippedList):
    print "    Testing core request handling...",
    helper.checkPageResult('Request handling', infoMap, code, testList, failedList)
