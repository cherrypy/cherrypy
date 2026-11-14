import os

import cherrypy
from cherrypy import tools
from cherrypy.test import helper


localDir = os.path.dirname(__file__)
logfile = os.path.join(localDir, 'test_misc_tools.log')


def setup_server():
    class Root:
        @cherrypy.expose
        def index(self):
            yield 'Hello, world'

        h = [('Content-Language', 'en-GB'), ('Content-Type', 'text/plain')]
        tools.response_headers(headers=h)(index)

        # A fixed, known Last-Modified value that's independent of any
        # file's own mtime, so If-Modified-Since/If-Unmodified-Since
        # can be tested with dates before/after/equal to it -- the
        # general REST-app scenario from GH #976, as opposed to static
        # file serving where the file's own mtime always matches the
        # client's cached value exactly.
        conditional_last_modified = cherrypy.lib.httputil.HTTPDate(1500000000)

        @cherrypy.expose
        def conditional(self):
            cherrypy.response.headers['Last-Modified'] = (
                self.conditional_last_modified
            )
            cherrypy.lib.cptools.validate_since()
            return 'resource content'

        @cherrypy.expose
        @cherrypy.config(
            **{
                'tools.response_headers.on': True,
                'tools.response_headers.headers': [
                    ('Content-Language', 'fr'),
                    ('Content-Type', 'text/plain'),
                ],
                'tools.log_hooks.on': True,
            },
        )
        def other(self):
            return 'salut'

    @cherrypy.config(**{'tools.accept.on': True})
    class Accept:
        @cherrypy.expose
        def index(self):
            return '<a href="feed">Atom feed</a>'

        @cherrypy.expose
        @tools.accept(media='application/atom+xml')
        def feed(self):
            return """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
    <title>Unknown Blog</title>
</feed>"""

        @cherrypy.expose
        def select(self):
            # We could also write this: mtype = cherrypy.lib.accept.accept(...)
            mtype = tools.accept.callable(['text/html', 'text/plain'])
            if mtype == 'text/html':
                return '<h2>Page Title</h2>'
            else:
                return 'PAGE TITLE'

    class Referer:
        @cherrypy.expose
        def accept(self):
            return 'Accepted!'

        reject = accept

    class AutoVary:
        @cherrypy.expose
        def index(self):
            # Read a header directly with 'get'
            cherrypy.request.headers.get('Accept-Encoding')
            # Read a header directly with '__getitem__'
            cherrypy.request.headers['Host']
            # Read a header directly with '__contains__'
            'If-Modified-Since' in cherrypy.request.headers
            # Read a header directly
            'Range' in cherrypy.request.headers
            # Call a lib function
            tools.accept.callable(['text/html', 'text/plain'])
            return 'Hello, world!'

    conf = {
        '/referer': {
            'tools.referer.on': True,
            'tools.referer.pattern': r'http://[^/]*example\.com',
        },
        '/referer/reject': {
            'tools.referer.accept': False,
            'tools.referer.accept_missing': True,
        },
        '/autovary': {'tools.autovary.on': True},
    }

    root = Root()
    root.referer = Referer()
    root.accept = Accept()
    root.autovary = AutoVary()
    cherrypy.tree.mount(root, config=conf)
    cherrypy.config.update({'log.error_file': logfile})


class ResponseHeadersTest(helper.CPWebCase):
    setup_server = staticmethod(setup_server)

    def testResponseHeadersDecorator(self):
        self.getPage('/')
        self.assertHeader('Content-Language', 'en-GB')
        self.assertHeader('Content-Type', 'text/plain;charset=utf-8')


class ValidateSinceTest(helper.CPWebCase):
    """Regression tests for GH #976.

    validate_since() previously required an exact string match
    between If-Modified-Since/If-Unmodified-Since and Last-Modified,
    rather than an actual date comparison as RFC 7232 requires --
    this only happened to work for static file serving, where the
    served file's own mtime naturally matches exactly, but broke for
    general REST-style resources whose Last-Modified doesn't
    necessarily match a client's date byte-for-byte.
    """

    setup_server = staticmethod(setup_server)

    def test_if_modified_since_future_date(self):
        # A date strictly after Last-Modified must still trigger 304,
        # not just an exact match.
        self.getPage(
            '/conditional',
            headers=[
                ('If-Modified-Since', 'Fri, 18 Jul 2017 07:20:00 GMT'),
            ],
        )
        self.assertStatus(304)

    def test_if_modified_since_exact_match(self):
        # The existing exact-match case must still work.
        self.getPage(
            '/conditional',
            headers=[
                ('If-Modified-Since', 'Fri, 14 Jul 2017 02:40:00 GMT'),
            ],
        )
        self.assertStatus(304)

    def test_if_modified_since_past_date(self):
        # A date before Last-Modified must NOT trigger 304 -- the
        # resource has changed since then.
        self.getPage(
            '/conditional',
            headers=[
                ('If-Modified-Since', 'Mon, 10 Jul 2017 00:00:00 GMT'),
            ],
        )
        self.assertStatus('200 OK')
        self.assertBody('resource content')

    def test_if_unmodified_since_future_date(self):
        # The resource is (trivially) unmodified as of any date after
        # its own Last-Modified, so the request must succeed.
        self.getPage(
            '/conditional',
            headers=[
                ('If-Unmodified-Since', 'Fri, 18 Jul 2017 07:20:00 GMT'),
            ],
        )
        self.assertStatus('200 OK')

    def test_if_unmodified_since_past_date(self):
        # The resource HAS been modified since a date before its
        # Last-Modified, so the precondition must fail with 412.
        self.getPage(
            '/conditional',
            headers=[
                ('If-Unmodified-Since', 'Mon, 10 Jul 2017 00:00:00 GMT'),
            ],
        )
        self.assertStatus(412)

    def test_if_modified_since_malformed_date(self):
        # A malformed date must not crash the request; it's simply
        # treated as not matching/not applicable.
        self.getPage(
            '/conditional',
            headers=[('If-Modified-Since', 'not a valid http-date')],
        )
        self.assertStatus('200 OK')

    def testResponseHeaders(self):
        self.getPage('/other')
        self.assertHeader('Content-Language', 'fr')
        self.assertHeader('Content-Type', 'text/plain;charset=utf-8')


class RefererTest(helper.CPWebCase):
    setup_server = staticmethod(setup_server)

    def testReferer(self):
        self.getPage('/referer/accept')
        self.assertErrorPage(403, 'Forbidden Referer header.')

        self.getPage(
            '/referer/accept',
            headers=[('Referer', 'http://www.example.com/')],
        )
        self.assertStatus(200)
        self.assertBody('Accepted!')

        # Reject
        self.getPage('/referer/reject')
        self.assertStatus(200)
        self.assertBody('Accepted!')

        self.getPage(
            '/referer/reject',
            headers=[('Referer', 'http://www.example.com/')],
        )
        self.assertErrorPage(403, 'Forbidden Referer header.')


class AcceptTest(helper.CPWebCase):
    setup_server = staticmethod(setup_server)

    def test_Accept_Tool(self):
        # Test with no header provided
        self.getPage('/accept/feed')
        self.assertStatus(200)
        self.assertInBody('<title>Unknown Blog</title>')

        # Specify exact media type
        self.getPage(
            '/accept/feed',
            headers=[('Accept', 'application/atom+xml')],
        )
        self.assertStatus(200)
        self.assertInBody('<title>Unknown Blog</title>')

        # Specify matching media range
        self.getPage('/accept/feed', headers=[('Accept', 'application/*')])
        self.assertStatus(200)
        self.assertInBody('<title>Unknown Blog</title>')

        # Specify all media ranges
        self.getPage('/accept/feed', headers=[('Accept', '*/*')])
        self.assertStatus(200)
        self.assertInBody('<title>Unknown Blog</title>')

        # Specify unacceptable media types
        self.getPage('/accept/feed', headers=[('Accept', 'text/html')])
        self.assertErrorPage(
            406,
            'Your client sent this Accept header: text/html. '
            'But this resource only emits these media types: '
            'application/atom+xml.',
        )

        # Test resource where tool is 'on' but media is None (not set).
        self.getPage('/accept/')
        self.assertStatus(200)
        self.assertBody('<a href="feed">Atom feed</a>')

    def test_accept_selection(self):
        # Try both our expected media types
        self.getPage('/accept/select', [('Accept', 'text/html')])
        self.assertStatus(200)
        self.assertBody('<h2>Page Title</h2>')
        self.getPage('/accept/select', [('Accept', 'text/plain')])
        self.assertStatus(200)
        self.assertBody('PAGE TITLE')
        self.getPage(
            '/accept/select',
            [('Accept', 'text/plain, text/*;q=0.5')],
        )
        self.assertStatus(200)
        self.assertBody('PAGE TITLE')

        # text/* and */* should prefer text/html since it comes first
        # in our 'media' argument to tools.accept
        self.getPage('/accept/select', [('Accept', 'text/*')])
        self.assertStatus(200)
        self.assertBody('<h2>Page Title</h2>')
        self.getPage('/accept/select', [('Accept', '*/*')])
        self.assertStatus(200)
        self.assertBody('<h2>Page Title</h2>')

        # Try unacceptable media types
        self.getPage('/accept/select', [('Accept', 'application/xml')])
        self.assertErrorPage(
            406,
            'Your client sent this Accept header: application/xml. '
            'But this resource only emits these media types: '
            'text/html, text/plain.',
        )


class AutoVaryTest(helper.CPWebCase):
    setup_server = staticmethod(setup_server)

    def testAutoVary(self):
        self.getPage('/autovary/')
        self.assertHeader(
            'Vary',
            'Accept, Accept-Charset, Accept-Encoding, '
            'Host, If-Modified-Since, Range',
        )
