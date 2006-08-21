"""Test the various means of instantiating and invoking tools."""

import gzip, StringIO
import types
import test
test.prefer_parent_path()

import cherrypy
from cherrypy import _cptools, tools


europoundUnicode = u'\x80\xa3'

def setup_server():
    
    def check_access():
        if not getattr(cherrypy.request, "login", None):
            raise cherrypy.HTTPError(401)
    tools.check_access = _cptools.Tool('before_request_body', check_access)
    
    def numerify():
        def number_it(body):
            for chunk in body:
                for k, v in cherrypy.request.numerify_map:
                    chunk = chunk.replace(k, v)
                yield chunk
        cherrypy.response.body = number_it(cherrypy.response.body)
    
    class NumTool(_cptools.Tool):
        def _setup(self):
            def makemap():
                m = self._merged_args().get("map", {})
                cherrypy.request.numerify_map = m.items()
            cherrypy.request.hooks.attach('on_start_resource', makemap)
            
            def critical():
                cherrypy.request.error_response = cherrypy.HTTPError(502).set_response
            critical.failsafe = True
            cherrypy.request.hooks.attach('on_start_resource', critical)
            
            cherrypy.request.hooks.attach(self._point, self.callable)
    
    tools.numerify = NumTool('before_finalize', numerify)
    
    # It's not mandatory to inherit from _cptools.Tool.
    class NadsatTool:
        
        def __init__(self):
            self.counter = 0
            self.ended = {}
            self._name = "nadsat"
            
        def nadsat(self):
            def nadsat_it_up(body):
                for chunk in body:
                    chunk = chunk.replace("good", "horrorshow")
                    chunk = chunk.replace("piece", "lomtick")
                    yield chunk
            cherrypy.response.body = nadsat_it_up(cherrypy.response.body)
        
        def cleanup(self):
            # This runs after the request has been completely written out.
            cherrypy.response.body = "razdrez"
            self.ended[cherrypy.request.counter] = True
        cleanup.failsafe = True
        
        def _setup(self):
            cherrypy.request.counter = self.counter = self.counter + 1
            self.ended[cherrypy.request.counter] = False
            cherrypy.request.hooks.callbacks['before_finalize'].insert(0, self.nadsat)
            cherrypy.request.hooks.attach('on_end_request', self.cleanup)
    tools.nadsat = NadsatTool()
    
    def pipe_body():
        cherrypy.request.process_request_body = False
        clen = int(cherrypy.request.headers['Content-Length'])
        cherrypy.request.body = cherrypy.request.rfile.read(clen)
    
    class Root:
        def index(self):
            return "Howdy earth!"
        index.exposed = True
        
        def euro(self):
            yield u"Hello,"
            yield u"world"
            yield europoundUnicode
        euro.exposed = True
        
        # Bare hooks
        def pipe(self):
            return cherrypy.request.body
        pipe.exposed = True
        pipe._cp_config = {'hooks.before_request_body': pipe_body}
        
        # Multiple decorators; include kwargs just for fun.
        def decorated_euro(self):
            yield u"Hello,"
            yield u"world"
            yield europoundUnicode
        decorated_euro.exposed = True
        decorated_euro = tools.gzip(compress_level=6)(decorated_euro)
        decorated_euro = tools.encode(errors='ignore')(decorated_euro)
    
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
    
    
    # METHOD ONE:
    # Declare Tools in _cp_config
    class Demo(Test):
        
        _cp_config = {"tools.nadsat.on": True}
        
        def index(self):
            return "A good piece of cherry pie"
        
        def ended(self, id):
            return repr(tools.nadsat.ended[int(id)])
        
        def err(self):
            raise ValueError()
        
        def errinstream(self):
            raise ValueError()
            yield "confidential"
        
        # METHOD TWO: decorator using Tool()
        # We support Python 2.3, but the @-deco syntax would look like this:
        # @tools.check_access()
        def restricted(self):
            return "Welcome!"
        restricted = tools.check_access()(restricted)
        
        def err_in_onstart(self):
            return "success!"
    
    
    cherrypy.config.update({'log_to_screen': False,
                            'environment': 'production',
                            'show_tracebacks': True,
                            })
    
    conf = {
        # METHOD THREE:
        # Declare Tools in detached config
        '/demo': {
            'tools.numerify.on': True,
            'tools.numerify.map': {"pie": "3.14159"},
        },
        '/demo/restricted': {
            'show_tracebacks': False,
        },
        '/demo/errinstream': {
            'stream_response': True,
        },
        '/demo/err_in_onstart': {
            # Because this isn't a dict, on_start_resource will error.
            'tools.numerify.map': "pie->3.14159"
        },
        # Combined tools
        '/euro': {
            'tools.gzip.on': True,
            'tools.encode.on': True,
        },
    }
    cherrypy.tree.mount(root, conf=conf)


#                             Client-side code                             #

import helper


class ToolTests(helper.CPWebCase):
    
    def testDemo(self):
        self.getPage("/demo/")
        # If body is "razdrez", then on_end_request is being called too early.
        self.assertBody("A horrorshow lomtick of cherry 3.14159")
        # If this fails, then on_end_request isn't being called at all.
        self.getPage("/demo/ended/1")
        self.assertBody("True")
        
        valerr = '\n    raise ValueError()\nValueError'
        self.getPage("/demo/err")
        # If body is "razdrez", then on_end_request is being called too early.
        self.assertErrorPage(502, pattern=valerr)
        # If this fails, then on_end_request isn't being called at all.
        self.getPage("/demo/ended/3")
        self.assertBody("True")
        
        # If body is "razdrez", then on_end_request is being called too early.
        self.getPage("/demo/errinstream")
        # Because this error is raised after the response body has
        # started, the status should not change to an error status.
        self.assertStatus("200 OK")
        self.assertBody("Unrecoverable error in the server.")
        # If this fails, then on_end_request isn't being called at all.
        self.getPage("/demo/ended/5")
        self.assertBody("True")
        
        # Test the "__call__" technique (compile-time decorator).
        self.getPage("/demo/restricted")
        self.assertErrorPage(401)
    
    def testGuaranteedHooks(self):
        # The 'critical' on_start_resource hook is 'failsafe' (guaranteed
        # to run even if there are failures in other on_start methods).
        # This is NOT true of the other hooks.
        # Here, we have set up a failure in NumerifyTool.numerify_map,
        # but our 'critical' hook should run and set the error to 502.
        self.getPage("/demo/err_in_onstart")
        self.assertErrorPage(502)
        self.assertInBody("AttributeError: 'str' object has no attribute 'items'")
    
    def testCombinedTools(self):
        expectedResult = (u"Hello,world" + europoundUnicode).encode('utf-8')
        zbuf = StringIO.StringIO()
        zfile = gzip.GzipFile(mode='wb', fileobj=zbuf, compresslevel=9)
        zfile.write(expectedResult)
        zfile.close()
        
        self.getPage("/euro", headers=[("Accept-Encoding", "gzip")])
        self.assertInBody(zbuf.getvalue()[:3])
        
        zbuf = StringIO.StringIO()
        zfile = gzip.GzipFile(mode='wb', fileobj=zbuf, compresslevel=6)
        zfile.write(expectedResult)
        zfile.close()
        
        self.getPage("/decorated_euro", headers=[("Accept-Encoding", "gzip")])
        self.assertInBody(zbuf.getvalue()[:3])
    
    def testBareHooks(self):
        content = "bit of a pain in me gulliver"
        self.getPage("/pipe",
                     headers=[("Content-Length", len(content)),
                              ("Content-Type", "text/plain")],
                     method="POST", body=content)
        self.assertBody(content)


if __name__ == '__main__':
    setup_server()
    helper.testmain()

