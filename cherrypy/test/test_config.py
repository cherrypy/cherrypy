"""Tests for the CherryPy configuration system."""
import test
test.prefer_parent_path()

import StringIO
import cherrypy


def setup_server():
    
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
        embed = index
        
        def wrong(self):
            conf = "\n[global]\nserver.environment = production\n"
            cherrypy.config.update(file=StringIO.StringIO(conf))
        wrong.exposed=True
    
    cherrypy.tree.mount(Root())
    cherrypy.root.foo = Foo()
    
    cherrypy.config.update({
        'global': {'server.log_to_screen': False,
                   'server.environment': 'production',
                   'server.show_tracebacks': True,
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
    })

    _env_conf = {'/': {'server.environment': 'development'},
                 '/prod': {'server.environment': 'production'},
                 '/embed': {'server.environment': 'embedded'},
                 }
    cherrypy.tree.mount(Env(), "/env", _env_conf)

    # Shortcut syntax--should get put in the "global" bucket
    cherrypy.config.update({'luxuryyacht': 'throatwobblermangrove'})


#                             Client-side code                             #

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
            # If 'foo' == 'this', then the mount point '/env' leaks into '/'.
            ('/env/prod','foo', 'None'),
        ]
        for path, key, expected in tests:
            self.getPage(path + "?key=" + key)
            self.assertBody(expected)
    
    def testUnrepr(self):
        err = ('WrongConfigValue: ("section: '
               "'global', option: 'server.environment', value: 'production'"
               '''", 'UnknownType', ('production',))''')
        self.getPage("/env/wrong")
        self.assertErrorPage(500, pattern=err)
    
    def testEnvironments(self):
        for key, val in cherrypy.config.environments['development'].iteritems():
            self.getPage("/env/?key=" + key)
            # The dev environment will have logdebuginfo data
            data = self.body.split("\n")[0]
            self.assertEqual(data, str(val))
        for key, val in cherrypy.config.environments['production'].iteritems():
            self.getPage("/env/prod/?key=" + key)
            self.assertBody(str(val))
        for key, val in cherrypy.config.environments['embedded'].iteritems():
            self.getPage("/env/embed/?key=" + key)
            data = self.body.split("\n")[0]
            self.assertEqual(data, str(val))


if __name__ == '__main__':
    setup_server()
    helper.testmain()
