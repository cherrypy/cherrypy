"""Test the various means of instantiating and invoking filters."""

import types
import test
test.prefer_parent_path()

import cherrypy
from cherrypy import filters
from cherrypy.filters.basefilter import BaseFilter


class Numerify(BaseFilter):
    
    def before_finalize(self):
        if not cherrypy.config.get("numerify_filter.on", False):
            return
        
        def number_it(body):
            for chunk in body:
                chunk = chunk.replace("pie", "3.14159")
                yield chunk
        cherrypy.response.body = number_it(cherrypy.response.body)


class AccessFilter(BaseFilter):
    
    def before_request_body(self):
        if not cherrypy.config.get("access_filter.on", False):
            return
        
        if not getattr(cherrypy.request, "login", None):
            raise cherrypy.HTTPError(401)


# It's not mandatory to inherit from BaseFilter.
class NadsatFilter:
    
    def before_finalize(self):
        self.ended = False
        def nadsat_it_up(body):
            for chunk in body:
                chunk = chunk.replace("good", "horrorshow")
                chunk = chunk.replace("piece", "lomtick")
                yield chunk
        cherrypy.response.body = nadsat_it_up(cherrypy.response.body)
    
    def on_end_request(self):
        # This runs after the request has been completely written out.
        cherrypy.response.body = "razdrez"
        self.ended = True



class Root:
    def index(self):
        return "Howdy earth!"
    index.exposed = True

cherrypy.root = Root()


class TestType(type):
    """Metaclass which automatically exposes all functions in each subclass,
    and adds an instance of the subclass as an attribute of cherrypy.root.
    """
    def __init__(cls, name, bases, dct):
        type.__init__(name, bases, dct)
        for value in dct.itervalues():
            if isinstance(value, types.FunctionType):
                value.exposed = True
        setattr(cherrypy.root, name.lower(), cls())
class Test(object):
    __metaclass__ = TestType


class CPFilterList(Test):
    
    # METHOD ONE:
    # Use _cp_filters (old name: _cpFilterList)
    _cp_filters = [NadsatFilter()]
    
    def index(self):
        return "A good piece of cherry pie"
    
    def err(self):
        raise ValueError()
    
    def errinstream(self):
        raise ValueError()
        yield "confidential"
    
    def restricted(self):
        return "Welcome!"


cherrypy.config.update({
    'global': {
        # METHOD TWO:
        # Declare a classname in server.input_filters.
        'server.input_filters': ["cherrypy.test.test_custom_filters.AccessFilter"],
        'server.log_to_screen': False,
        'server.environment': 'production',
        'server.show_tracebacks': True,
    },
    '/cpfilterlist': {
        'numerify_filter.on': True,
    },
    '/cpfilterlist/restricted': {
        'access_filter.on': True,
        'server.show_tracebacks': False,
    },
    '/cpfilterlist/errinstream': {
        'streamResponse': True,
    },
})

# METHOD THREE:
# Insert a class directly into the filters.output_filters chain.
# You can also insert a string, but we're effectively testing
# using-a-string via the config file.
filters.output_filters.insert(0, Numerify)

# We have to call filters.init() here (if we want methods #2 and #3
# to work), because the test suite may already have run server.start()
# (which is where filters.init() is usually called).
filters.init()

import helper


class FilterTests(helper.CPWebCase):
    
    def testCPFilterList(self):
        # Lazily import _nf, since filters.__init__ will reimport this module.
        _nf = cherrypy.root.cpfilterlist._cp_filters[0]
        
        self.getPage("/cpfilterlist/")
        # If body is "razdrez", then on_end_request is being called too early.
        self.assertBody("A horrorshow lomtick of cherry 3.14159")
        # If this fails, then on_end_request isn't being called at all.
        self.assertEqual(_nf.ended, True)
        
        ignore = helper.webtest.ignored_exceptions
        ignore.append(ValueError)
        try:
            valerr = '\n    raise ValueError()\nValueError'
            self.getPage("/cpfilterlist/err")
            # If body is "razdrez", then on_end_request is being called too early.
            self.assertErrorPage(500, pattern=valerr)
            # If this fails, then on_end_request isn't being called at all.
            self.assertEqual(_nf.ended, True)
            
            # If body is "razdrez", then on_end_request is being called too early.
            if cherrypy.server.httpserver is None:
                self.assertRaises(ValueError, self.getPage,
                                  "/cpfilterlist/errinstream")
            else:
                self.getPage("/cpfilterlist/errinstream")
                # Because this error is raised after the response body has
                # started, the status should not change to an error status.
                self.assertStatus("200 OK")
                self.assertBody("Unrecoverable error in the server.")
            # If this fails, then on_end_request isn't being called at all.
            self.assertEqual(_nf.ended, True)
        finally:
            ignore.pop()
        
        # Test the config method.
        self.getPage("/cpfilterlist/restricted")
        self.assertErrorPage(401)


if __name__ == '__main__':
    helper.testmain()

