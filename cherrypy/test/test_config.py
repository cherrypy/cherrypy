"""Tests for the CherryPy configuration system."""

from cherrypy.test import test
test.prefer_parent_path()

import os
import StringIO
import cherrypy


def setup_server():
    
    class Root:
        
        _cp_config = {'foo': 'this',
                      'bar': 'that'}
        
        def __init__(self):
            cherrypy.config.namespaces['db'] = self.db_namespace
        
        def db_namespace(self, k, v):
            if k == "scheme":
                self.db = v
        
        # @cherrypy.expose(alias=('global_', 'xyz'))
        def index(self, key):
            return cherrypy.request.config.get(key, "None")
        index = cherrypy.expose(index, alias=('global_', 'xyz'))
        
        def repr(self, key):
            return repr(cherrypy.request.config.get(key, None))
        repr.exposed = True
        
        def dbscheme(self):
            return self.db
        dbscheme.exposed = True
    
    class Foo:
        
        _cp_config = {'foo': 'this2',
                      'baz': 'that2'}
        
        def index(self, key):
            return cherrypy.request.config.get(key, "None")
        index.exposed = True
        nex = index
        
        def bar(self, key):
            return `cherrypy.request.config.get(key, None)`
        bar.exposed = True
        bar._cp_config = {'foo': 'this3', 'bax': 'this4'}
    
    class Another:
        
        def index(self, key):
            return str(cherrypy.request.config.get(key, "None"))
        index.exposed = True
    
    
    def raw_namespace(key, value):
        if key == 'input.map':
            params = cherrypy.request.params
            for name, coercer in value.iteritems():
                try:
                    params[name] = coercer(params[name])
                except KeyError:
                    pass
        elif key == 'output':
            handler = cherrypy.request.handler
            def wrapper():
                # 'value' is a type (like int or str).
                return value(handler())
            cherrypy.request.handler = wrapper
    
    class Raw:
        
        _cp_config = {'raw.output': repr}
        
        def incr(self, num):
            return num + 1
        incr.exposed = True
        incr._cp_config = {'raw.input.map': {'num': int}}
    
    ioconf = StringIO.StringIO("""
[/]
neg: -1234
filename: os.path.join(os.getcwd(), "hello.py")
""")
    
    root = Root()
    root.foo = Foo()
    root.raw = Raw()
    app = cherrypy.tree.mount(root, config=ioconf)
    app.request_class.namespaces['raw'] = raw_namespace
    
    cherrypy.tree.mount(Another(), "/another")
    cherrypy.config.update({'environment': 'test_suite',
                            'luxuryyacht': 'throatwobblermangrove',
                            'db.scheme': r"sqlite///memory",
                            })


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
            ('/foo/bar', 'baz', "'that2'"),
            ('/foo/nex', 'baz', 'that2'),
            # If 'foo' == 'this', then the mount point '/another' leaks into '/'.
            ('/another/','foo', 'None'),
        ]
        for path, key, expected in tests:
            self.getPage(path + "?key=" + key)
            self.assertBody(expected)
        
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
        for key, expected in expectedconf.iteritems():
            self.getPage("/foo/bar?key=" + key)
            self.assertBody(`expected`)
    
    def testUnrepr(self):
        self.getPage("/repr?key=neg")
        self.assertBody("-1234")
        
        self.getPage("/repr?key=filename")
        self.assertBody(repr(os.path.join(os.getcwd(), "hello.py")))
    
    def testCustomNamespaces(self):
        self.getPage("/raw/incr?num=12")
        self.assertBody("13")
        
        self.getPage("/dbscheme")
        self.assertBody(r"sqlite///memory")


if __name__ == '__main__':
    setup_server()
    helper.testmain()
