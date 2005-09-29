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
from cherrypy.lib import cptools
import types
import os
localDir = os.path.dirname(__file__)


class Root:
    
    def index(self):
        return "hello"
    index.exposed = True
    
    def _global(self):
        pass
    _global.exposed = True

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


class Params(Test):
    
    def index(self, thing):
        return repr(thing)
    
    def ismap(self, x, y):
        return "Coordinates: %s, %s" % (x, y)
    
    def default(self, *args, **kwargs):
        return "args: %s kwargs: %s" % (args, kwargs)


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
    
    def _cpOnError(self):
        raise cherrypy.HTTPRedirect("/errpage")
    
    def error(self):
        raise NameError()
    
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
        elif user_id == "terrier":
            # Trade it for a fish when redirecting
            raise cherrypy.InternalRedirect('/image/getImagesByUser',
                                           {"user_id": "fish"})
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
    
    def custom(self):
        raise cherrypy.HTTPError(404)
    
    def page_method(self):
        raise ValueError()
    
    def page_yield(self):
        yield "hello"
        raise ValueError()
    
    def page_streamed(self):
        yield "hello"
        raise ValueError()
        yield "very oops"
    
    def cause_err_in_finalize(self):
        # Since status must start with an int, this should error.
        cherrypy.response.status = "ZOO OK"


class Ranges(Test):
    
    def get_ranges(self):
        return repr(cptools.getRanges(8))
    
    def slice_file(self):
        path = os.path.join(os.getcwd(), os.path.dirname(__file__))
        return cptools.serveFile(os.path.join(path, "static/index.html"))


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
    
    def parameterized(self, data):
        return data
    
    def request_body(self):
        # This should be a file object (temp file),
        # which CP will just pipe back out if we tell it to.
        return cherrypy.request.body

class Cookies(Test):
    
    def single(self, name):
        cookie = cherrypy.request.simpleCookie[name]
        cherrypy.response.simpleCookie[name] = cookie.value
    
    def multiple(self, names):
        for name in names:
            cookie = cherrypy.request.simpleCookie[name]
            cherrypy.response.simpleCookie[name] = cookie.value

class MaxRequestSize(Test):
    
    def index(self):
        return "OK"

    def upload(self, file):
        return "Size: %s" % len(file.file.read())

class ThreadLocal(Test):
    
    def index(self):
        existing = repr(getattr(cherrypy.request, "asdf", None))
        cherrypy.request.asdf = "hello"
        return existing


logFile = os.path.join(localDir, "error.log")
logAccessFile = os.path.join(localDir, "access.log")

cherrypy.config.update({
    'global': {'server.logToScreen': False,
               'server.environment': 'production',
               'server.showTracebacks': True,
               'server.protocolVersion': "HTTP/1.1",
               },
    '/': {
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
    '/flatten': {
        'server.logFile': logFile,
        'server.logAccessFile': logAccessFile,
    },
    '/params': {
        'server.logFile': logFile,
    },
    '/error': {
        'server.logFile': logFile,
        'server.logTracebacks': True,
    },
    '/error/page_streamed': {
        'streamResponse': True,
    },
    '/error/cause_err_in_finalize': {
        'server.showTracebacks': False,
    },
    '/error/custom': {
        'errorPage.404': "nonexistent.html",
    },
})

# Shortcut syntax--should get put in the "global" bucket
cherrypy.config.update({'luxuryyacht': 'throatwobblermangrove'})

import helper

class CoreRequestHandlingTest(helper.CPWebCase):
    
    def testConfig(self):
        tests = [
            ('global',   'luxuryyacht', 'throatwobblermangrove'),
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
        cherrypy.request.purge__()
        for path, key, expected in tests:
            cherrypy.request.path = path
            result = cherrypy.config.get(key, None)
            self.assertEqual(result, expected)
    
    def testParams(self):
        self.getPage("/params/?thing=a")
        self.assertBody("'a'")
        
        self.getPage("/params/?thing=a&thing=b&thing=c")
        self.assertBody("['a', 'b', 'c']")
        
        # Test friendly error message when given params are not accepted.
        ignore = helper.webtest.ignored_exceptions
        ignore.append(TypeError)
        try:
            self.getPage("/params/?notathing=meeting")
            self.assertInBody("TypeError: index() got an unexpected keyword argument 'notathing'")
        finally:
            ignore.pop()
        
        # Test "% HEX HEX"-encoded URL, param keys, and values
        self.getPage("/params/%d4%20%e3/cheese?Gruy%E8re=Bulgn%e9ville")
        self.assertBody(r"args: ('\xd4 \xe3', 'cheese') "
                        r"kwargs: {'Gruy\xe8re': 'Bulgn\xe9ville'}")
        
        # Make sure that encoded = and & get parsed correctly
        self.getPage("/params/code?url=http%3A//cherrypy.org/index%3Fa%3D1%26b%3D2")
        self.assertBody(r"args: ('code',) "
                        r"kwargs: {'url': 'http://cherrypy.org/index?a=1&b=2'}")
        
        # Test coordinates sent by <img ismap>
        self.getPage("/params/ismap?223,114")
        self.assertBody("Coordinates: 223, 114")
    
    def testStatus(self):
        self.getPage("/status/")
        self.assertBody('normal')
        self.assertStatus('200 OK')
        
        self.getPage("/status/blank")
        self.assertBody('')
        self.assertStatus('200 OK')
        
        self.getPage("/status/illegal")
        self.assertStatus('500 Internal error')
        msg = "Illegal response status from server (out of range)."
        self.assertErrorPage(500, msg)
        
        self.getPage("/status/unknown")
        self.assertBody('funky')
        self.assertStatus('431 My custom error')
        
        self.getPage("/status/bad")
        self.assertStatus('500 Internal error')
        msg = "Illegal response status from server (non-numeric)."
        self.assertErrorPage(500, msg)
    
    def testLogging(self):
        open(logFile, "wb").write("")
        open(logAccessFile, "wb").write("")
        
        self.getPage("/flatten/as_string")
        self.assertBody('content')
        self.assertStatus('200 OK')
        
        self.getPage("/flatten/as_yield")
        self.assertBody('content')
        self.assertStatus('200 OK')
        
        data = open(logAccessFile, "rb").readlines()
        self.assertEqual(data[0][:15], '127.0.0.1 - - [')
        haslength = False
        for k, v in self.headers:
            if k.lower() == 'content-length':
                haslength = True
        if haslength:
            self.assertEqual(data[0][-42:], '] "GET /flatten/as_string HTTP/1.1" 200 7\n')
        else:
            self.assertEqual(data[0][-42:], '] "GET /flatten/as_string HTTP/1.1" 200 -\n')
        
        self.assertEqual(data[1][:15], '127.0.0.1 - - [')
        haslength = False
        for k, v in self.headers:
            if k.lower() == 'content-length':
                haslength = True
        if haslength:
            self.assertEqual(data[1][-41:], '] "GET /flatten/as_yield HTTP/1.1" 200 7\n')
        else:
            self.assertEqual(data[1][-41:], '] "GET /flatten/as_yield HTTP/1.1" 200 -\n')
        
        data = open(logFile, "rb").readlines()
        self.assertEqual(data, [])
        
        # Test that error log gets access messages if no logAccess defined.
        self.getPage("/params/?thing=a")
        self.assertBody("'a'")
        data = open(logFile, "rb").readlines()
        self.assertEqual(data[0][-53:], ' HTTP INFO 127.0.0.1 - GET /params/?thing=a HTTP/1.1\n')
        
        # Test that tracebacks get written to the error log.
        ignore = helper.webtest.ignored_exceptions
        ignore.append(ValueError)
        try:
            self.getPage("/error/page_method")
            self.assertInBody("raise ValueError()")
            data = open(logFile, "rb").readlines()
            self.assertEqual(data[2][-41:], ' INFO Traceback (most recent call last):\n')
            self.assertEqual(data[8], '    raise ValueError()\n')
        finally:
            ignore.pop()
    
    def testRedirect(self):
        self.getPage("/redirect/")
        self.assertBody('child')
        self.assertStatus('200 OK')
        
        self.getPage("/redirect?id=3")
        self.assert_(self.status in ('302 Found', '303 See Other'))
        self.assertInBody("<a href='http://127.0.0.1:8000/redirect/?id=3'>"
                          "http://127.0.0.1:8000/redirect/?id=3</a>")
        
        self.getPage("/redirect/by_code?code=300")
        self.assertMatchesBody(r"<a href='(.*)somewhere else'>\1somewhere else</a>")
        self.assertStatus('300 Multiple Choices')
        
        self.getPage("/redirect/by_code?code=301")
        self.assertMatchesBody(r"<a href='(.*)somewhere else'>\1somewhere else</a>")
        self.assertStatus('301 Moved Permanently')
        
        self.getPage("/redirect/by_code?code=302")
        self.assertMatchesBody(r"<a href='(.*)somewhere else'>\1somewhere else</a>")
        self.assertStatus('302 Found')
        
        self.getPage("/redirect/by_code?code=303")
        self.assertMatchesBody(r"<a href='(.*)somewhere else'>\1somewhere else</a>")
        self.assertStatus('303 See Other')
        
        self.getPage("/redirect/by_code?code=307")
        self.assertMatchesBody(r"<a href='(.*)somewhere else'>\1somewhere else</a>")
        self.assertStatus('307 Temporary Redirect')
        
        self.getPage("/redirect/nomodify")
        self.assertBody('')
        self.assertStatus('304 Not modified')
        
        self.getPage("/redirect/proxy")
        self.assertBody('')
        self.assertStatus('305 Use Proxy')
        
        # InternalRedirect
        self.getPage("/redirect/internal")
        self.assertBody('hello')
        self.assertStatus('200 OK')
        
        self.getPage("/redirect/internal2?user_id=Sir-not-appearing-in-this-film")
        self.assertBody('0 images for Sir-not-appearing-in-this-film')
        self.assertStatus('200 OK')
        
        self.getPage("/redirect/internal2?user_id=parrot")
        self.assertBody('0 images for slug')
        self.assertStatus('200 OK')
        
        self.getPage("/redirect/internal2?user_id=terrier")
        self.assertBody('0 images for fish')
        self.assertStatus('200 OK')
        
        # HTTPRedirect on error
        self.getPage("/redirect/error")
        self.assertStatus('303 See Other')
        self.assertInBody('/errpage')
    
    def testFlatten(self):
        for url in ["/flatten/as_string", "/flatten/as_list",
                    "/flatten/as_yield", "/flatten/as_dblyield",
                    "/flatten/as_refyield"]:
            self.getPage(url)
            self.assertBody('content')
    
    def testErrorHandling(self):
        self.getPage("/error/missing")
        self.assertStatus("404 Not Found")
        self.assertErrorPage(404, "The path '/error/missing' was not found.")
        
        ignore = helper.webtest.ignored_exceptions
        ignore.append(ValueError)
        try:
            valerr = r'\n    raise ValueError\(\)\nValueError\n'
            self.getPage("/error/page_method")
            self.assertErrorPage(500, pattern=valerr)
            
            self.getPage("/error/page_yield")
            self.assertErrorPage(500, pattern=valerr)
            
            import cherrypy
            # streamResponse should be True for this path.
            if cherrypy._httpserver is None:
                self.assertRaises(ValueError, self.getPage,
                                  "/error/page_streamed")
            else:
                self.getPage("/error/page_streamed")
                # Because this error is raised after the response body has
                # started, the status should not change to an error status.
                self.assertStatus("200 OK")
                self.assertBody("helloUnrecoverable error in the server.")
            
            # No traceback should be present
            self.getPage("/error/cause_err_in_finalize")
            msg = "Illegal response status from server (non-numeric)."
            self.assertErrorPage(500, msg, None)
        finally:
            ignore.pop()
        
        # Test error in custom error page (ticket #305).
        self.getPage("/error/custom")
        self.assertStatus("404 Not Found")
        msg = ("Nothing matches the given URI<br />"
               "In addition, the custom error page failed:\n<br />"
               "[Errno 2] No such file or directory: 'nonexistent.html'")
        self.assertInBody(msg)

    
    def test_Ranges(self):
        self.getPage("/ranges/get_ranges", [('Range', 'bytes=3-6')])
        self.assertBody("[(3, 7)]")
        
        # Test multiple ranges and a suffix-byte-range-spec, for good measure.
        self.getPage("/ranges/get_ranges", [('Range', 'bytes=2-4,-1')])
        self.assertBody("[(2, 5), (7, 8)]")
        
        # Get a partial file.
        self.getPage("/ranges/slice_file", [('Range', 'bytes=2-5')])
        self.assertStatus("206 Partial Content")
        self.assertHeader("Content-Type", "text/html")
        self.assertHeader("Content-Range", "bytes 2-5/14")
        self.assertBody("llo,")
        
        # What happens with overlapping ranges (and out of order, too)?
        self.getPage("/ranges/slice_file", [('Range', 'bytes=4-6,2-5')])
        self.assertStatus("206 Partial Content")
        ct = ""
        for k, v in self.headers:
            if k.lower() == "content-type":
                ct = v
                break
        expected_type = "multipart/byteranges; boundary="
        self.assert_(ct.startswith(expected_type))
        boundary = ct[len(expected_type):]
        expected_body = """--%s
Content-type: text/html
Content-range: bytes 4-6/14

o, w
--%s
Content-type: text/html
Content-range: bytes 2-5/14

llo, 
--%s""" % (boundary, boundary, boundary)
        self.assertBody(expected_body)
        self.assertHeader("Content-Length")
        
        # Test "416 Requested Range Not Satisfiable"
        self.getPage("/ranges/slice_file", [('Range', 'bytes=2300-2900')])
        self.assertStatus("416 Requested Range Not Satisfiable")
        self.assertHeader("Content-Range", "bytes */14")
    
    def testHeaderCaseSensitivity(self):
        # Tests that each header only appears once, regardless of case.
        self.getPage("/headers/")
        self.assertBody("double header test")
        hnames = [name.title() for name, val in self.headers]
        for key in ['Content-Length', 'Content-Type', 'Date',
                    'Expires', 'Location', 'Server']:
            self.assertEqual(hnames.count(key), 1)
    
    def testHTTPMethods(self):
        # Test that all defined HTTP methods work.
        for m in defined_http_methods:
            h = []
            self.getPage("/method/", method=m)
            
            # HEAD requests should not return any body.
            if m == "HEAD":
                m = ""
            
            self.assertBody(m)
        
        # Request a PUT method with a form-urlencoded body
        self.getPage("/method/parameterized", method="PUT",
                       body="data=on+top+of+other+things")
        self.assertBody("on top of other things")
        
        # Request a PUT method with a file body
        h = [("Content-type", "text/plain"),
             ("Content-Length", "27")]
        
        self.getPage("/method/request_body", headers=h, method="PUT",
                       body="one thing on top of another")
        self.assertBody("one thing on top of another")
        
        # Request a disallowed method
        self.getPage("/method/", method="LINK")
        self.assertStatus("405 Method Not Allowed")
        
        # Request an unknown method
        self.getPage("/method/", method="SEARCH")
        self.assertStatus("501 Not Implemented")
        
        # Request the OPTIONS method with a Request-URI of "*".
        self.getPage("*", method="OPTIONS")
        self.assertStatus("200 OK")
        # Content-Length header required for OPTIONS with no response body.
        # See http://www.w3.org/Protocols/rfc2616/rfc2616-sec9.html#sec9.2
        self.assertHeader("Content-Length", "0")
    
    def testFavicon(self):
        # Calls to favicon.ico are special-cased in _cphttptools.
        icofilename = os.path.join(localDir, "../favicon.ico")
        icofile = open(icofilename, "rb")
        data = icofile.read()
        icofile.close()
        
        self.getPage("/favicon.ico")
        self.assertBody(data)
        
        self.getPage("/redirect/favicon.ico")
        self.assertBody(data)
    
    def testCookies(self):
        self.getPage("/cookies/single?name=First",
                     [('Cookie', 'First=Dinsdale;')])
        self.assertHeader('Set-Cookie', 'First=Dinsdale;')
        
        self.getPage("/cookies/multiple?names=First&names=Last",
                     [('Cookie', 'First=Dinsdale; Last=Piranha;'),
                      ])
        self.assertHeader('Set-Cookie', 'First=Dinsdale;')
        self.assertHeader('Set-Cookie', 'Last=Piranha;')

    def testMaxRequestSize(self):
        self.getPage("/maxrequestsize/index")
        self.assertBody("OK")
        
        if cherrypy._httpserver.__class__.__name__ == "WSGIServer":
            cherrypy.config.update({'server.maxRequestHeaderSize': 10})
            self.getPage("/maxrequestsize/index")
            self.assertStatus("413 Request Entity Too Large")
            self.assertBody("Request Entity Too Large")
            cherrypy.config.update({'server.maxRequestHeaderSize': 0})
        
        # Test upload
        h = [("Content-type", "multipart/form-data; boundary=x"),
             ("Content-Length", "110")]
        b = """--x
Content-Disposition: form-data; name="file"; filename="hello.txt"
Content-Type: text/plain

hello
--x--
"""
        self.getPage('/maxrequestsize/upload', h, "POST", b)
        self.assertBody('Size: 5')
        
        if cherrypy._httpserver.__class__.__name__ == "WSGIServer":
            cherrypy.config.update({
                '/maxrequestsize': {'server.maxRequestBodySize': 3}})
            self.getPage('/maxrequestsize/upload', h, "POST", b)
            self.assertStatus("413 Request Entity Too Large")
            self.assertInBody("Request Entity Too Large")
    
    def testEmptyThreadlocals(self):
        results = []
        for x in xrange(20):
            self.getPage("/threadlocal/")
            results.append(self.body)
        self.assertEqual(results, ["None"] * 20)


if __name__ == '__main__':
    helper.testmain()
