"""Tests for the CherryPy configuration system."""
from cherrypy.test import test
test.prefer_parent_path()

import StringIO
import cherrypy


def setup_server():
    
    class Root:
        
        _cp_config = {'foo': 'this',
                      'bar': 'that'}
        
        def index(self, key):
            return cherrypy.config.get(key, "None")
        index.exposed = True
        global_ = index
        xyz = index
    
    class Foo:
        
        _cp_config = {'foo': 'this2',
                      'baz': 'that2'}
        
        def index(self, key):
            return cherrypy.config.get(key, "None")
        index.exposed = True
        nex = index
        
        def bar(self, key):
            return cherrypy.config.get(key, "None")
        bar.exposed = True
        bar._cp_config = {'foo': 'this3', 'bax': 'this4'}
    
    class Env:
        
        def index(self, key):
            return str(cherrypy.config.get(key, "None"))
        index.exposed = True
        prod = index
        embed = index
    
    root = Root()
    root.foo = Foo()
    cherrypy.tree.mount(root)
    
    cherrypy.config.update({'log_to_screen': False,
                            'environment': 'production',
                            'show_tracebacks': True,
                            })
    
    _env_conf = {'/': {'environment': 'development'},
                 '/prod': {'environment': 'production'},
                 '/embed': {'environment': 'embedded'},
                 }
    cherrypy.tree.mount(Env(), "/env", _env_conf)
    
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
    
    def testEnvironments(self):
        for key, val in cherrypy.config.environments['development'].iteritems():
            self.getPage("/env/?key=" + key)
            self.assertBody(str(val))
        for key, val in cherrypy.config.environments['production'].iteritems():
            self.getPage("/env/prod/?key=" + key)
            self.assertBody(str(val))
        for key, val in cherrypy.config.environments['embedded'].iteritems():
            self.getPage("/env/embed/?key=" + key)
            self.assertBody(str(val))


if __name__ == '__main__':
    setup_server()
    helper.testmain()
