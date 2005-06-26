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

import cherrypy
import types

class Root:
    def index(self):
        return "hello"
    index.exposed = True

cherrypy.root = Root()


class TestType(type):
    def __init__(cls, name, bases, dct):
        type.__init__(name, bases, dct)
        for value in dct.itervalues():
            if isinstance(value, types.FunctionType):
                value.exposed = True
        setattr(cherrypy.root, name.lower(), cls())
class Test(object):
    __metaclass__ = TestType


class Status(Test):
    
    def index(self):
        return "normal"
    
    def blank(self):
        cherrypy.response.status = ""
    
    # According to RFC 2616, new status codes are OK as long as they
    # are between 100 and 599.
    
    # Here is an illegal code...
    def illegal(self):
        cherrypy.response.status = 781
        return "oops"
    
    # ...and here is an unknown but legal code.
    def unknown(self):
        cherrypy.response.status = "431 My custom error"
        return "funky"
    
    # Non-numeric code
    def bad(self):
        cherrypy.response.status = "error"
        return "hello"


class Redirect(Test):
    
    def index(self):
        return "child"
    
    def by_code(self, code):
        raise cherrypy.HTTPRedirect("somewhere else", code)
    
    def nomodify(self):
        raise cherrypy.HTTPRedirect("", 304)
    
    def proxy(self):
        raise cherrypy.HTTPRedirect("proxy", 305)
    
    def internal(self):
        raise cherrypy.InternalRedirect("/")
    
    def internal2(self, user_id):
        if user_id == "parrot":
            # Trade it for a slug when redirecting
            raise cherrypy.InternalRedirect('/image/getImagesByUser',
                                           "user_id=slug")
        else:
            raise cherrypy.InternalRedirect('/image/getImagesByUser')


class Image(Test):
    
    def getImagesByUser(self, user_id):
        return "0 images for %s" % user_id


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
        cherrypy.response.headerMap["Content-Length"] = 39
        def inner():
            yield "hello"
            raise ValueError
            yield "oops"
        return inner()


class Headers(Test):
    
    def index(self):
        # From http://www.cherrypy.org/ticket/165:
        # "header field names should not be case sensitive sayes the rfc.
        # if i set a headerfield in complete lowercase i end up with two
        # header fields, one in lowercase, the other in mixed-case."
        
        # Set the most common headers
        hMap = cherrypy.response.headerMap
        hMap['content-type'] = "text/html"
        hMap['content-length'] = 18
        hMap['server'] = 'CherryPy headertest'
        hMap['location'] = ('%s://127.0.0.1:8000/headers/'
                            % cherrypy.request.scheme)
        
        # Set a rare header for fun
        hMap['Expires'] = 'Thu, 01 Dec 2194 16:00:00 GMT'
        
        return "double header test"


defined_http_methods = ("OPTIONS", "GET", "HEAD", "POST", "PUT", "DELETE",
                        "TRACE", "CONNECT")
class Method(Test):
    
    def index(self):
        m = cherrypy.request.method
        if m in defined_http_methods:
            return m
        
        if m == "LINK":
            cherrypy.response.status = 405
        else:
            cherrypy.response.status = 501


cherrypy.config.update({
    'global': {
        'server.logToScreen': False,
        'server.environment': 'production',
        'foo': 'this',
        'bar': 'that',
    },
    '/foo': {
        'foo': 'this2',
        'baz': 'that2',
    },
    '/foo/bar': {
        'foo': 'this3',
        'bax': 'this4',
    },
})
cherrypy.server.start(initOnly=True)

import unittest
import helper
import os

class CoreRequestHandlingTest(unittest.TestCase):
    
    def testConfig(self):
        import cherrypy
        tests = [
            ('/',        'nex', None   ),
            ('/',        'foo', 'this' ),
            ('/',        'bar', 'that' ),
            ('/xyz',     'foo', 'this' ),
            ('/foo',     'foo', 'this2'),
            ('/foo',     'bar', 'that' ),
            ('/foo',     'bax', None   ),
            ('/foo/bar', 'baz', 'that2'),
            ('/foo/nex', 'baz', 'that2'),
        ]
        for path, key, expected in tests:
            cherrypy.request.path = path
            result = cherrypy.config.get(key, None)
            self.assertEqual(result, expected)
    
    def testStatus(self):
        helper.request("/status/")
        self.assertEqual(cherrypy.response.body, 'normal')
        self.assertEqual(cherrypy.response.status, '200 OK')
        
        helper.request("/status/blank")
        self.assertEqual(cherrypy.response.body, '')
        self.assertEqual(cherrypy.response.status, '200 OK')
        
        helper.request("/status/illegal")
        self.assertEqual(cherrypy.response.body, 'oops')
        self.assertEqual(cherrypy.response.status, '500 Internal error')
        
        helper.request("/status/unknown")
        self.assertEqual(cherrypy.response.body, 'funky')
        self.assertEqual(cherrypy.response.status, '431 My custom error')
        
        helper.request("/status/bad")
        self.assertEqual(cherrypy.response.body, 'hello')
        self.assertEqual(cherrypy.response.status, '500 Internal error')
    
    def testRedirect(self):
        helper.request("/redirect/")
        self.assertEqual(cherrypy.response.body, 'child')
        self.assertEqual(cherrypy.response.status, '200 OK')
        
        helper.request("/redirect?id=3")
        self.assert_(cherrypy.response.status in ('302 Found', '303 See Other'))
        self.assert_("<a href='http://127.0.0.1:8000/redirect/?id=3'>http://127.0.0.1:8000/redirect/?id=3</a>"
                     in cherrypy.response.body)
        
        helper.request("/redirect/by_code?code=300")
        self.assert_("<a href='somewhere else'>somewhere else</a>" in cherrypy.response.body)
        self.assertEqual(cherrypy.response.status, '300 Multiple Choices')
        
        helper.request("/redirect/by_code?code=301")
        self.assert_("<a href='somewhere else'>somewhere else</a>" in cherrypy.response.body)
        self.assertEqual(cherrypy.response.status, '301 Moved Permanently')
        
        helper.request("/redirect/by_code?code=302")
        self.assert_("<a href='somewhere else'>somewhere else</a>" in cherrypy.response.body)
        self.assertEqual(cherrypy.response.status, '302 Found')
        
        helper.request("/redirect/by_code?code=303")
        self.assert_("<a href='somewhere else'>somewhere else</a>" in cherrypy.response.body)
        self.assertEqual(cherrypy.response.status, '303 See Other')
        
        helper.request("/redirect/by_code?code=307")
        self.assert_("<a href='somewhere else'>somewhere else</a>" in cherrypy.response.body)
        self.assertEqual(cherrypy.response.status, '307 Temporary Redirect')
        
        helper.request("/redirect/nomodify")
        self.assertEqual(cherrypy.response.body, '')
        self.assertEqual(cherrypy.response.status, '304 Not modified')
        
        helper.request("/redirect/proxy")
        self.assertEqual(cherrypy.response.body, '')
        self.assertEqual(cherrypy.response.status, '305 Use Proxy')
        
        # InternalRedirect
        helper.request("/redirect/internal")
        self.assertEqual(cherrypy.response.body, 'hello')
        self.assertEqual(cherrypy.response.status, '200 OK')
        
        helper.request("/redirect/internal2?user_id=Sir-not-appearing-in-this-film")
        self.assertEqual(cherrypy.response.body, '0 images for Sir-not-appearing-in-this-film')
        self.assertEqual(cherrypy.response.status, '200 OK')
        
        helper.request("/redirect/internal2?user_id=parrot")
        self.assertEqual(cherrypy.response.body, '0 images for slug')
        self.assertEqual(cherrypy.response.status, '200 OK')
    
    def testFlatten(self):
        for url in ["/flatten/as_string", "/flatten/as_list",
                    "/flatten/as_yield", "/flatten/as_dblyield",
                    "/flatten/as_refyield"]:
            helper.request(url)
            self.assertEqual(cherrypy.response.body, 'content')
    
    def testErrorHandling(self):
        valerr = '\n    raise ValueError\nValueError\n'
        helper.request("/error/page_method")
        self.assert_(cherrypy.response.body.endswith(valerr))
        
        helper.request("/error/page_yield")
        self.assert_(cherrypy.response.body.endswith(valerr))
        
        if cherrypy._httpserver is None:
            self.assertRaises(ValueError, helper.request, "/error/page_http_1_1")
        else:
            helper.request("/error/page_http_1_1")
            # Because this error is raised after the response body has
            # started, the status should not change to an error status.
            self.assertEqual(cherrypy.response.status, "200 OK")
            self.assertEqual(cherrypy.response.body, "helloUnrecoverable error in the server.")
    
    def testHeaderCaseSensitivity(self):
        helper.request("/headers/")
        self.assertEqual(cherrypy.response.body, "double header test")
        hnames = [name.title() for name, val in cherrypy.response.headers]
        hnames.sort()
        self.assertEqual(hnames, ['Content-Length', 'Content-Type', 'Date', 'Expires',
                                  'Location', 'Server'])
    
    def testMethods(self):
        # Test that all defined HTTP methods work.
        for m in defined_http_methods:
            h = []
            helper.request("/method/", method=m)
            
            # HEAD requests should not return any body.
            if m == "HEAD":
                m = ""
            
            self.assertEqual(cherrypy.response.body, m)
        
        # Request a disallowed method
        helper.request("/method/", method="LINK")
        self.assertEqual(cherrypy.response.status, "405 Method Not Allowed")
        
        # Request an unknown method
        helper.request("/method/", method="SEARCH")
        self.assertEqual(cherrypy.response.status, "501 Not Implemented")
    
    def testFavicon(self):
        # Calls to favicon.ico are special-cased in _cphttptools.
        localDir = os.path.dirname(__file__)
        icofilename = os.path.join(localDir, "../favicon.ico")
        icofile = open(icofilename, "rb")
        data = icofile.read()
        icofile.close()
        
        helper.request("/favicon.ico")
        self.assertEqual(cherrypy.response.body, data)
        
        helper.request("/redirect/favicon.ico")
        self.assertEqual(cherrypy.response.body, data)


if __name__ == '__main__':
    unittest.main()
