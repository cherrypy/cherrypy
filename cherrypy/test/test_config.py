"""Tests for the CherryPy configuration system."""

from cherrypy.test import test
test.prefer_parent_path()

import StringIO
import cherrypy


def setup_server():
    
    class Root:
        
        _cp_config = {'foo': 'this',
                      'bar': 'that'}
        
        # @cherrypy.expose(alias=('global_', 'xyz'))
        def index(self, key):
            return cherrypy.request.config.get(key, "None")
        index = cherrypy.expose(index, alias=('global_', 'xyz'))
        
        def repr(self, key):
            return repr(cherrypy.request.config.get(key, None))
        repr.exposed = True
    
    class Foo:
        
        _cp_config = {'foo': 'this2',
                      'baz': 'that2'}
        
        def index(self, key):
            return cherrypy.request.config.get(key, "None")
        index.exposed = True
        nex = index
        
        def bar(self, key):
            return cherrypy.request.config.get(key, "None")
        bar.exposed = True
        bar._cp_config = {'foo': 'this3', 'bax': 'this4'}
    
    class Another:
        
        def index(self, key):
            return str(cherrypy.request.config.get(key, "None"))
        index.exposed = True
    
    ioconf = StringIO.StringIO("""
[/]
neg: -1234
""")
    
    root = Root()
    root.foo = Foo()
    cherrypy.tree.mount(root, config=ioconf)
    cherrypy.tree.mount(Another(), "/another")
    cherrypy.config.update({'environment': 'test_suite'})
    
    # Shortcut syntax--should get put in the "global" bucket
    cherrypy.config.update({'luxuryyacht': 'throatwobblermangrove'})


#                             Client-side code                             #

from cherrypy.test import helper

class ConfigTests(helper.CPWebCase):
    
    def testConfig(self):
        tests = [
            ('/',        'nex', 'None'),
            ('/',        'foo', 'this'),
            ('/',        'bar', 'that'),
            ('/repr',    'neg', '-1234'),
            ('/xyz',     'foo', 'this'),
            ('/foo/',    'foo', 'this2'),
            ('/foo/',    'bar', 'that'),
            ('/foo/',    'bax', 'None'),
            ('/foo/bar', 'baz', 'that2'),
            ('/foo/nex', 'baz', 'that2'),
            # If 'foo' == 'this', then the mount point '/another' leaks into '/'.
            ('/another/','foo', 'None'),
        ]
        for path, key, expected in tests:
            self.getPage(path + "?key=" + key)
            self.assertBody(expected)
    
    def testExternalDispatch(self):
        # 'cherrypy.request' should reference a default instance
        cherrypy.request.app = cherrypy.tree.apps[""]
        cherrypy.request.dispatch("/foo/bar")
        expectedconf = {
            # From CP defaults
            'tools.log_headers.on': False,
            'tools.log_tracebacks.on': True,
            'request.show_tracebacks': True,
            'log.screen': False,
            'environment': 'test_suite',
            'engine.autoreload_on': False,
            # From global config
            'luxuryyacht': 'throatwobblermangrove',
            # From Root._cp_config
            'bar': 'that',
            # From Foo._cp_config
            'baz': 'that2',
            # From Foo.bar._cp_config
            'foo': 'this3',
            'bax': 'this4',
            }
        for k, v in expectedconf.iteritems():
            self.assertEqual(cherrypy.request.config[k], v)


if __name__ == '__main__':
    setup_server()
    helper.testmain()
