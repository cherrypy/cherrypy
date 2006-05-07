"""Test the various means of instantiating and invoking filters."""

import types
import test
test.prefer_parent_path()

import cherrypy
from cherrypy import tools


def setup_server():
    
    def check_access():
        if not getattr(cherrypy.request, "login", None):
            raise cherrypy.HTTPError(401)
    tools.check_access = tools.Tool('before_request_body', check_access)
    
    def numerify():
        def number_it(body):
            for chunk in body:
                for k, v in cherrypy.request.numerify_map:
                    chunk = chunk.replace(k, v)
                yield chunk
        cherrypy.response.body = number_it(cherrypy.response.body)
    
    class NumTool(tools.Tool):
        def setup(self):
            def makemap():
                m = self.merged_args().get("map", {})
                cherrypy.request.numerify_map = m.items()
            cherrypy.request.hooks.attach('on_start_resource', makemap)
            cherrypy.request.hooks.attach(self.point, self.callable)
    tools.numerify = NumTool('before_finalize', numerify)
    
    # It's not mandatory to inherit from tools.Tool.
    class NadsatTool:
        
        def __init__(self):
            self.counter = 0
            self.ended = {}
            self.name = "nadsat"
        
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
        
        def setup(self):
            cherrypy.request.counter = self.counter = self.counter + 1
            self.ended[cherrypy.request.counter] = False
            cherrypy.request.hooks.callbacks['before_finalize'].insert(0, self.nadsat)
            cherrypy.request.hooks.attach('on_end_request', self.cleanup)
    tools.nadsat = NadsatTool()
    
    class Root:
        def index(self):
            return "Howdy earth!"
        index.exposed = True
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
    # Use _cp_config
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
        
        # METHOD TWO: decorator using tool.wrap
        def restricted(self):
            return "Welcome!"
        restricted = tools.check_access.wrap()(restricted)
        
        def err_in_onstart(self):
            return "success!"
    
    
    cherrypy.config.update({'log_to_screen': False,
                            'environment': 'production',
                            'show_tracebacks': True,
                            })
    
    conf = {
        # METHOD THREE:
        # Do it all in config
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
    }
    cherrypy.tree.mount(root, conf=conf)


#                             Client-side code                             #

import helper


class FilterTests(helper.CPWebCase):
    
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
        self.assertErrorPage(500, pattern=valerr)
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
        
        # Test the decorator technique.
        self.getPage("/demo/restricted")
        self.assertErrorPage(401)
    
    def testGuaranteedFilters(self):
        # The on_start_resource and on_end_request filter methods are all
        # guaranteed to run, even if there are failures in other on_start
        # or on_end methods. This is NOT true of the other filter methods.
        # Here, we have set up a failure in NumerifyFilter.on_start_resource,
        # but because that failure is logged and passed over, the error
        # page we obtain in the user agent should be from before_finalize.
        self.getPage("/demo/err_in_onstart")
        self.assertErrorPage(500)
        self.assertInBody("AttributeError: 'Request' object has no "
                          "attribute 'numerify_map'")


if __name__ == '__main__':
    setup_server()
    helper.testmain()

