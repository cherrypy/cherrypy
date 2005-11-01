"""Tests for the CherryPy configuration system."""

import cherrypy

class Root:
    def index(self, key):
        return cherrypy.config.get(key, "None")
    index.exposed = True
    global_ = index
    xyz = index

class Foo:
    def index(self, key):
        return cherrypy.config.get(key, "None")
    index.exposed = True
    bar = index
    nex = index

class Env:
    def index(self, key):
        return str(cherrypy.config.get(key, "None"))
    index.exposed = True
    prod = index

cherrypy.root = Root()
cherrypy.root.foo = Foo()
cherrypy.root.env = Env()
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
    '/env': {'server.environment': 'development'},
    '/env/prod': {'server.environment': 'production'},
})

# Shortcut syntax--should get put in the "global" bucket
cherrypy.config.update({'luxuryyacht': 'throatwobblermangrove'})

import helper

class ConfigTests(helper.CPWebCase):
    
    def testConfig(self):
        tests = [
            ('*',        'luxuryyacht', 'throatwobblermangrove'),
            ('/',        'nex', 'None'),
            ('/',        'foo', 'this'),
            ('/',        'bar', 'that'),
            ('/xyz',     'foo', 'this'),
            ('/foo/',    'foo', 'this2'),
            ('/foo/',    'bar', 'that'),
            ('/foo/',    'bax', 'None'),
            ('/foo/bar', 'baz', 'that2'),
            ('/foo/nex', 'baz', 'that2'),
        ]
        for path, key, expected in tests:
            self.getPage(path + "?key=" + key)
            self.assertBody(expected)
    
    def testEnvironments(self):
        for key, val in cherrypy.config.environments['development'].iteritems():
            self.getPage("/env/?key=" + key)
            # The dev environment will have logdebuginfo data
            self.assertEqual(self.body.split("\n")[0], str(val))
        for key, val in cherrypy.config.environments['production'].iteritems():
            self.getPage("/env/prod/?key=" + key)
            self.assertBody(str(val))


if __name__ == '__main__':
    helper.testmain()
