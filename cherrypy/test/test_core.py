"""Basic tests for the CherryPy core: request handling."""

import test
test.prefer_parent_path()

import cherrypy
from cherrypy import tools
from cherrypy.lib import httptools, static
import types

import os
localDir = os.path.dirname(__file__)
log_file = os.path.join(localDir, "error.log")
log_access_file = os.path.join(localDir, "access.log")
favicon_path = os.path.join(os.getcwd(), localDir, "../favicon.ico")

defined_http_methods = ("OPTIONS", "GET", "HEAD", "POST", "PUT", "DELETE",
                        "TRACE", "CONNECT")


def setup_server():
    class Root:
        
        def index(self):
            return "hello"
        index.exposed = True
        
        favicon_ico = tools.staticfile.handler(filename=favicon_path)
        
        def andnow(self):
            return "the larch"
        andnow.exposed = True
        
        def global_(self):
            pass
        global_.exposed = True
        
        def delglobal(self):
            del self.__class__.__dict__['global_']
        delglobal.exposed = True
        
        def defct(self, newct):
            newct = "text/%s" % newct
            cherrypy.config.update({'default_content_type': newct})
        defct.exposed = True
        
        def upload(self, file):
            return "Size: %s" % len(file.file.read())
        upload.exposed = True
    
    root = Root()


    class TestType(type):
        """Metaclass which automatically exposes all functions in each subclass,
        and adds an instance of the subclass as an attribute of root.
        """
        def __init__(cls, name, bases, dct):
            type.__init__(name, bases, dct)
            for value in dct.itervalues():
                if isinstance(value, types.FunctionType):
                    value.exposed = True
            setattr(root, name.lower(), cls())
    class Test(object):
        __metaclass__ = TestType


    class Params(Test):
        
        _cp_config = {'log_file': log_file}
        
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
            return "bad news"


    class Redirect(Test):
        
        class Error:
            _cp_config = {"tools.err_redirect.on": True,
                          "tools.err_redirect.url": "/errpage",
                          }
            
            def index(self):
                raise NameError()
            index.exposed = True
        error = Error()
        
        def index(self):
            return "child"
        
        def by_code(self, code):
            raise cherrypy.HTTPRedirect("somewhere else", code)
        
        def nomodify(self):
            raise cherrypy.HTTPRedirect("", 304)
        
        def proxy(self):
            raise cherrypy.HTTPRedirect("proxy", 305)
        
        def stringify(self):
            return str(cherrypy.HTTPRedirect("/"))
    
    
    def login_redir():
        if not getattr(cherrypy.request, "login", None):
            raise cherrypy.InternalRedirect("/internalredirect/login")
    tools.login_redir = tools.Tool('before_main', login_redir)
    
    class InternalRedirect(Test):
        
        def index(self):
            raise cherrypy.InternalRedirect("/")
        
        def petshop(self, user_id):
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
        
        @tools.login_redir.wrap()
        def secure(self):
            return "Welcome!"
        
        def login(self):
            return "Please log in"


    class Image(Test):
        
        def getImagesByUser(self, user_id):
            return "0 images for %s" % user_id


    class Flatten(Test):
        
        _cp_config = {'log_file': log_file, 'log_access_file': log_access_file,}
        
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
        
        _cp_config = {'log_file': log_file, 'tools.log_tracebacks.on': True}
        
        def custom(self):
            raise cherrypy.HTTPError(404, "No, <b>really</b>, not found!")
        custom._cp_config = {'error_page.404': os.path.join(localDir, "static/index.html")}
        
        def noexist(self):
            raise cherrypy.HTTPError(404, "No, <b>really</b>, not found!")
        noexist._cp_config = {'error_page.404': "nonexistent.html"}
        
        def page_method(self):
            raise ValueError()
        
        def page_yield(self):
            yield "howdy"
            raise ValueError()
        
        # We support Python 2.3, but the @-deco syntax would look like this:
        # @cherrypy.set_config(stream_response=True)
        def page_streamed(self):
            yield "word up"
            raise ValueError()
            yield "very oops"
        page_streamed = cherrypy.set_config(stream_response=True)(page_streamed)
        assert(page_streamed._cp_config == {'stream_response': True})
        
        def cause_err_in_finalize(self):
            # Since status must start with an int, this should error.
            cherrypy.response.status = "ZOO OK"
        cause_err_in_finalize._cp_config = {'show_tracebacks': False}
        
        def rethrow(self):
            """Test that an error raised here will be thrown out to the server."""
            raise ValueError()
        rethrow._cp_config = {'throw_errors': True}
    
    
    class Ranges(Test):
        
        def get_ranges(self):
            h = cherrypy.request.headers.get('Range')
            return repr(httptools.getRanges(h, 8))
        
        def slice_file(self):
            path = os.path.join(os.getcwd(), os.path.dirname(__file__))
            return static.serve_file(os.path.join(path, "static/index.html"))


    class Expect(Test):
        
        def expectation_failed(self):
            expect = cherrypy.request.headers.elements("Expect")
            if expect and expect[0].value != '100-continue':
                raise cherrypy.HTTPError(400)
            raise cherrypy.HTTPError(417, 'Expectation Failed')

    class Headers(Test):
        
        def doubledheaders(self):
            # From http://www.cherrypy.org/ticket/165:
            # "header field names should not be case sensitive sayes the rfc.
            # if i set a headerfield in complete lowercase i end up with two
            # header fields, one in lowercase, the other in mixed-case."
            
            # Set the most common headers
            hMap = cherrypy.response.headers
            hMap['content-type'] = "text/html"
            hMap['content-length'] = 18
            hMap['server'] = 'CherryPy headertest'
            hMap['location'] = ('%s://127.0.0.1:%s/headers/'
                                % (cherrypy.request.remote_port,
                                   cherrypy.request.scheme))
            
            # Set a rare header for fun
            hMap['Expires'] = 'Thu, 01 Dec 2194 16:00:00 GMT'
            
            return "double header test"


    class HeaderElements(Test):
        
        def get_elements(self, headername):
            e = cherrypy.request.headers.elements(headername)
            return "\n".join([str(x) for x in e])
    
    
    class Method(Test):
        
        def index(self):
            m = cherrypy.request.method
            if m in defined_http_methods:
                return m
            
            if m == "LINK":
                raise cherrypy.HTTPError(405)
            else:
                raise cherrypy.HTTPError(501)
        
        def parameterized(self, data):
            return data
        
        def request_body(self):
            # This should be a file object (temp file),
            # which CP will just pipe back out if we tell it to.
            return cherrypy.request.body

    class Divorce:
        """HTTP Method handlers shouldn't collide with normal method names.
        For example, a GET-handler shouldn't collide with a method named 'get'.
        
        If you build HTTP method dispatching into CherryPy, rewrite this class
        to use your new dispatch mechanism and make sure that:
            "GET /divorce HTTP/1.1" maps to divorce.index() and
            "GET /divorce/get?ID=13 HTTP/1.1" maps to divorce.get()
        """
        
        documents = {}
        
        def index(self):
            yield "<h1>Choose your document</h1>\n"
            yield "<ul>\n"
            for id, contents in self.documents:
                yield ("    <li><a href='/divorce/get?ID=%s'>%s</a>: %s</li>\n"
                       % (id, id, contents))
            yield "</ul>"
        index.exposed = True
        
        def get(self, ID):
            return ("Divorce document %s: %s" %
                    (ID, self.documents.get(ID, "empty")))
        get.exposed = True

    root.divorce = Divorce()


    class Cookies(Test):
        
        def single(self, name):
            cookie = cherrypy.request.simple_cookie[name]
            cherrypy.response.simple_cookie[name] = cookie.value
        
        def multiple(self, names):
            for name in names:
                cookie = cherrypy.request.simple_cookie[name]
                cherrypy.response.simple_cookie[name] = cookie.value


    class ThreadLocal(Test):
        
        def index(self):
            existing = repr(getattr(cherrypy.request, "asdf", None))
            cherrypy.request.asdf = "rassfrassin"
            return existing
    
    def check(login, password):
        # Dummy check_login_and_password function
        if login != 'login' or password != 'password':
            return u'Wrong login/password'
    
    cherrypy.config.update({
        'log_to_screen': False,
        'server.protocol_version': "HTTP/1.1",
        'environment': 'production',
        'show_tracebacks': True,
        'server.max_request_body_size': 200,
        'server.max_request_header_size': 500,
        })
    cherrypy.tree.mount(root)


#                             Client-side code                             #

import helper

class CoreRequestHandlingTest(helper.CPWebCase):
    
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
            self.assertInBody("index() got an unexpected keyword argument 'notathing'")
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
        self.assertStatus(200)
        
        self.getPage("/status/blank")
        self.assertBody('')
        self.assertStatus(200)
        
        self.getPage("/status/illegal")
        self.assertStatus(500)
        msg = "Illegal response status from server (out of range)."
        self.assertErrorPage(500, msg)
        
        self.getPage("/status/unknown")
        self.assertBody('funky')
        self.assertStatus(431)
        
        self.getPage("/status/bad")
        self.assertStatus(500)
        msg = "Illegal response status from server (non-numeric)."
        self.assertErrorPage(500, msg)
    
    def testLogging(self):
        open(log_file, "wb").write("")
        open(log_access_file, "wb").write("")
        
        self.getPage("/flatten/as_string")
        self.assertBody('content')
        self.assertStatus(200)
        
        self.getPage("/flatten/as_yield")
        self.assertBody('content')
        self.assertStatus(200)
        
        data = open(log_access_file, "rb").readlines()
        self.assertEqual(data[0][:15], '127.0.0.1 - - [')
        haslength = False
        for k, v in self.headers:
            if k.lower() == 'content-length':
                haslength = True
        if haslength:
            self.assert_(data[0].endswith('] "GET %s/flatten/as_string HTTP/1.1" 200 7 "" ""\n'
                                          % self.prefix()))
        else:
            self.assert_(data[0].endswith('] "GET %s/flatten/as_string HTTP/1.1" 200 - "" ""\n'
                                          % self.prefix()))
        
        self.assertEqual(data[1][:15], '127.0.0.1 - - [')
        haslength = False
        for k, v in self.headers:
            if k.lower() == 'content-length':
                haslength = True
        if haslength:
            self.assert_(data[1].endswith('] "GET %s/flatten/as_yield HTTP/1.1" 200 7 "" ""\n'
                                          % self.prefix()))
        else:
            self.assert_(data[1].endswith('] "GET %s/flatten/as_yield HTTP/1.1" 200 - "" ""\n'
                                          % self.prefix()))
        
        data = open(log_file, "rb").readlines()
        self.assertEqual(data, [])
        
        ignore = helper.webtest.ignored_exceptions
        ignore.append(ValueError)
        try:
            # Test that tracebacks get written to the error log.
            self.getPage("/error/page_method")
            self.assertInBody("raise ValueError()")
            data = open(log_file, "rb").readlines()
            self.assertEqual(data[0][-41:], ' INFO Traceback (most recent call last):\n')
            self.assertEqual(data[-3], '    raise ValueError()\n')
        finally:
            ignore.pop()
    
    def testRedirect(self):
        self.getPage("/redirect/")
        self.assertBody('child')
        self.assertStatus(200)
        
        # Test that requests for index methods without a trailing slash
        # get redirected to the same URI path with a trailing slash.
        # Make sure GET params are preserved.
        self.getPage("/redirect?id=3")
        self.assertStatus(('302 Found', '303 See Other'))
        self.assertInBody("<a href='http://127.0.0.1:%s%s/redirect/?id=3'>"
                          "http://127.0.0.1:%s%s/redirect/?id=3</a>" %
                          (self.PORT, self.prefix(), self.PORT, self.prefix()))
        
        if self.prefix():
            # Corner case: the "trailing slash" redirect could be tricky if
            # we're using a virtual root and the URI is "/vroot" (no slash).
            self.getPage("")
            self.assertStatus(('302 Found', '303 See Other'))
            self.assertInBody("<a href='http://127.0.0.1:%s%s/'>"
                              "http://127.0.0.1:%s%s/</a>" %
                              (self.PORT, self.prefix(), self.PORT, self.prefix()))
        
        self.getPage("/redirect/by_code?code=300")
        self.assertMatchesBody(r"<a href='(.*)somewhere else'>\1somewhere else</a>")
        self.assertStatus(300)
        
        self.getPage("/redirect/by_code?code=301")
        self.assertMatchesBody(r"<a href='(.*)somewhere else'>\1somewhere else</a>")
        self.assertStatus(301)
        
        self.getPage("/redirect/by_code?code=302")
        self.assertMatchesBody(r"<a href='(.*)somewhere else'>\1somewhere else</a>")
        self.assertStatus(302)
        
        self.getPage("/redirect/by_code?code=303")
        self.assertMatchesBody(r"<a href='(.*)somewhere else'>\1somewhere else</a>")
        self.assertStatus(303)
        
        self.getPage("/redirect/by_code?code=307")
        self.assertMatchesBody(r"<a href='(.*)somewhere else'>\1somewhere else</a>")
        self.assertStatus(307)
        
        self.getPage("/redirect/nomodify")
        self.assertBody('')
        self.assertStatus(304)
        
        self.getPage("/redirect/proxy")
        self.assertBody('')
        self.assertStatus(305)
        
        # InternalRedirect
        self.getPage("/internalredirect/")
        self.assertBody('hello')
        self.assertStatus(200)
        
        self.getPage("/internalredirect/petshop?user_id=Sir-not-appearing-in-this-film")
        self.assertBody('0 images for Sir-not-appearing-in-this-film')
        self.assertStatus(200)
        
        self.getPage("/internalredirect/petshop?user_id=parrot")
        self.assertBody('0 images for slug')
        self.assertStatus(200)
        
        self.getPage("/internalredirect/petshop?user_id=terrier")
        self.assertBody('0 images for fish')
        self.assertStatus(200)
        
        self.getPage("/internalredirect/secure")
        self.assertBody('Please log in')
        self.assertStatus(200)
        
        # HTTPRedirect on error
        self.getPage("/redirect/error/")
        self.assertStatus(('302 Found', '303 See Other'))
        self.assertInBody('/errpage')
        
        # Make sure str(HTTPRedirect()) works.
        self.getPage("/redirect/stringify", protocol="HTTP/1.0")
        self.assertStatus(200)
        self.assertBody("(['http://127.0.0.1:%s/'], 302)" % self.PORT)
        self.getPage("/redirect/stringify", protocol="HTTP/1.1")
        self.assertStatus(200)
        self.assertBody("(['http://127.0.0.1:%s/'], 303)" % self.PORT)
    
    def testFlatten(self):
        for url in ["/flatten/as_string", "/flatten/as_list",
                    "/flatten/as_yield", "/flatten/as_dblyield",
                    "/flatten/as_refyield"]:
            self.getPage(url)
            self.assertBody('content')
    
    def testErrorHandling(self):
        self.getPage("/error/missing")
        self.assertStatus(404)
        self.assertErrorPage(404, "The path '/error/missing' was not found.")
        
        ignore = helper.webtest.ignored_exceptions
        ignore.append(ValueError)
        try:
            valerr = '\n    raise ValueError()\nValueError'
            self.getPage("/error/page_method")
            self.assertErrorPage(500, pattern=valerr)
            
            self.getPage("/error/page_yield")
            self.assertErrorPage(500, pattern=valerr)
            
            self.getPage("/error/page_streamed")
            # Because this error is raised after the response body has
            # started, the status should not change to an error status.
            self.assertStatus(200)
            self.assertBody("word upUnrecoverable error in the server.")
            
            # No traceback should be present
            self.getPage("/error/cause_err_in_finalize")
            msg = "Illegal response status from server (non-numeric)."
            self.assertErrorPage(500, msg, None)
        finally:
            ignore.pop()
        
        # Test custom error page.
        self.getPage("/error/custom")
        self.assertStatus(404)
        self.assertEqual(len(self.body), 513)
        self.assertBody("Hello, world\r\n" + (" " * 499))
        
        # Test error in custom error page (ticket #305).
        # Note that the message is escaped for HTML (ticket #310).
        self.getPage("/error/noexist")
        self.assertStatus(404)
        msg = ("No, &lt;b&gt;really&lt;/b&gt;, not found!<br />"
               "In addition, the custom error page failed:\n<br />"
               "[Errno 2] No such file or directory: 'nonexistent.html'")
        self.assertInBody(msg)
##        
##        # Test throw_errors (ticket #186).
##        self.getPage("/error/rethrow")
##        self.assertBody("THROWN ERROR: ValueError")
    
    def testRanges(self):
        self.getPage("/ranges/get_ranges", [('Range', 'bytes=3-6')])
        self.assertBody("[(3, 7)]")
        
        # Test multiple ranges and a suffix-byte-range-spec, for good measure.
        self.getPage("/ranges/get_ranges", [('Range', 'bytes=2-4,-1')])
        self.assertBody("[(2, 5), (7, 8)]")
        
        # Get a partial file.
        self.getPage("/ranges/slice_file", [('Range', 'bytes=2-5')])
        self.assertStatus(206)
        self.assertHeader("Content-Type", "text/html")
        self.assertHeader("Content-Range", "bytes 2-5/14")
        self.assertBody("llo,")
        
        # What happens with overlapping ranges (and out of order, too)?
        self.getPage("/ranges/slice_file", [('Range', 'bytes=4-6,2-5')])
        self.assertStatus(206)
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
        self.assertStatus(416)
        self.assertHeader("Content-Range", "bytes */14")
        
        # Test Range behavior with HTTP/1.0 request
        self.getPage("/ranges/slice_file", [('Range', 'bytes=2-5')], protocol="HTTP/1.0")
        self.assertStatus(200)
        self.assertBody("Hello, world\r\n")
    
    def testExpect(self):
        e = ('Expect', '100-continue')
        self.getPage("/headerelements/get_elements?headername=Expect", [e])
        self.assertBody('100-continue')
        
        self.getPage("/expect/expectation_failed", [('Content-Length', '200'), e])
        self.assertStatus(417)
    
    def testHeaderElements(self):
        # Accept-* header elements should be sorted, with most preferred first.
        h = [('Accept', 'audio/*; q=0.2, audio/basic')]
        self.getPage("/headerelements/get_elements?headername=Accept", h)
        self.assertStatus(200)
        self.assertBody("audio/basic\n"
                        "audio/*;q=0.2")
        
        h = [('Accept', 'text/plain; q=0.5, text/html, text/x-dvi; q=0.8, text/x-c')]
        self.getPage("/headerelements/get_elements?headername=Accept", h)
        self.assertStatus(200)
        self.assertBody("text/x-c\n"
                        "text/html\n"
                        "text/x-dvi;q=0.8\n"
                        "text/plain;q=0.5")
        
        # Test that more specific media ranges get priority.
        h = [('Accept', 'text/*, text/html, text/html;level=1, */*')]
        self.getPage("/headerelements/get_elements?headername=Accept", h)
        self.assertStatus(200)
        self.assertBody("text/html;level=1\n"
                        "text/html\n"
                        "text/*\n"
                        "*/*")
        
        # Test Accept-Charset
        h = [('Accept-Charset', 'iso-8859-5, unicode-1-1;q=0.8')]
        self.getPage("/headerelements/get_elements?headername=Accept-Charset", h)
        self.assertStatus("200 OK")
        self.assertBody("iso-8859-5\n"
                        "unicode-1-1;q=0.8")
        
        # Test Accept-Encoding
        h = [('Accept-Encoding', 'gzip;q=1.0, identity; q=0.5, *;q=0')]
        self.getPage("/headerelements/get_elements?headername=Accept-Encoding", h)
        self.assertStatus("200 OK")
        self.assertBody("gzip;q=1.0\n"
                        "identity;q=0.5\n"
                        "*;q=0")
        
        # Test Accept-Language
        h = [('Accept-Language', 'da, en-gb;q=0.8, en;q=0.7')]
        self.getPage("/headerelements/get_elements?headername=Accept-Language", h)
        self.assertStatus("200 OK")
        self.assertBody("da\n"
                        "en-gb;q=0.8\n"
                        "en;q=0.7")
    
    def testHeaders(self):
        # Tests that each header only appears once, regardless of case.
        self.getPage("/headers/doubledheaders")
        self.assertBody("double header test")
        hnames = [name.title() for name, val in self.headers]
        for key in ['Content-Length', 'Content-Type', 'Date',
                    'Expires', 'Location', 'Server']:
            self.assertEqual(hnames.count(key), 1)
    
    def testHTTPMethods(self):
        # Test that all defined HTTP methods work.
        for m in defined_http_methods:
            self.getPage("/method/", method=m)
            
            # HEAD requests should not return any body.
            if m == "HEAD":
                self.assertBody("")
            elif m == "TRACE":
                # Some HTTP servers (like modpy) have their own TRACE support
                self.assertEqual(self.body[:5], "TRACE")
            else:
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
        self.assertStatus(405)
        
        # Request an unknown method
        self.getPage("/method/", method="SEARCH")
        self.assertStatus(501)
        
        # For method dispatchers: make sure that an HTTP method doesn't
        # collide with a virtual path atom. If you build HTTP-method
        # dispatching into the core, rewrite these handlers to use
        # your dispatch idioms.
        self.getPage("/divorce/get?ID=13")
        self.assertBody('Divorce document 13: empty')
        self.assertStatus(200)
        self.getPage("/divorce/", method="GET")
        self.assertBody('<h1>Choose your document</h1>\n<ul>\n</ul>')
        self.assertStatus(200)
    
    def testFavicon(self):
        # favicon.ico is served by staticfile.
        icofilename = os.path.join(localDir, "../favicon.ico")
        icofile = open(icofilename, "rb")
        data = icofile.read()
        icofile.close()
        
        self.getPage("/favicon.ico")
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
        self.getPage("/", headers=[('From', "x" * 500)])
        self.assertStatus(413)
        self.assertInBody("Request Entity Too Large")
        
        # Test for http://www.cherrypy.org/ticket/421
        # (Incorrect border condition in readline of SizeCheckWrapper).
        # This hangs in rev 891 and earlier.
        lines256 = "x" * 248
        self.getPage("/",
                     headers=[('Host', '127.0.0.1:%s' % self.PORT),
                              ('From', lines256)])
        
        # Test upload
        body = """--x
Content-Disposition: form-data; name="file"; filename="hello.txt"
Content-Type: text/plain

%s
--x--
"""
        b = body % ("x" * 96)
        h = [("Content-type", "multipart/form-data; boundary=x"),
             ("Content-Length", len(b))]
        self.getPage('/upload', h, "POST", b)
        self.assertBody('Size: 96')
        
        b = body % ("x" * 200)
        h = [("Content-type", "multipart/form-data; boundary=x"),
             ("Content-Length", len(b))]
        self.getPage('/upload', h, "POST", b)
        self.assertStatus(413)
        self.assertInBody("Request Entity Too Large")
    
    def testEmptyThreadlocals(self):
        results = []
        for x in xrange(20):
            self.getPage("/threadlocal/")
            results.append(self.body)
        self.assertEqual(results, ["None"] * 20)
    
    def testDefaultContentType(self):
        self.getPage('/')
        self.assertHeader('Content-Type', 'text/html')
        self.getPage('/defct/plain')
        self.getPage('/')
        self.assertHeader('Content-Type', 'text/plain')
        self.getPage('/defct/html')


if __name__ == '__main__':
    setup_server()
    helper.testmain()
