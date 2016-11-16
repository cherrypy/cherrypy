"""Simple test for HTTP PATCH requests."""

import cherrypy
from cherrypy.test import helper

class PatchRequestTests(helper.CPWebCase):

    @staticmethod
    def setup_server():
        """Sets up a basic cherryPy server for testing.
        """

        class Root(object):
            """Class to receive HTTP PATCH request. Has only 1 method 'patch'
            which receives a request with a URI query parameter and a body
            with data
            """
            exposed = True

            def _cp_dispatch(self, vpath):
                """Converts a URI from containing route parameters to a route 
                containing a query string.

                Example:
                from: http://example.com/noun/value 
                to  : http://example.com/noun?key=value

                Args:
                    vpath (str): The string of the

                Returns:
                    UserController
                """
                
                # since our routes will only contain the GUID, we'll only have 1 
                # path. If we have more, just ignore it
                if len(vpath) == 1:
                    cherrypy.request.params['key'] = vpath.pop()
                    
                return self


            def PATCH(self, **kwargs):
                """Makes sure that PATCH requests work

                Args:
                    kwargs (dict): values passed in the URI

                Returns:
                    str: the values from the URI and body
                """

                data = cherrypy.request.body.read()
                res  = 'key=' + kwargs['key'] + '|body='
                ret  = str.encode(res, 'utf-8') + data

                return ret

        conf = {
            '/': {
                'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            }
        }

        root = Root()

        cherrypy.tree.mount(root, '/root', config=conf)


    def test_HttpPatchMethod(self):
        b = 'patch request'
        h = [('Content-Type', 'text/plain'),
             ('Content-Length', str(len(b)))]
        self.getPage('/root/val', headers=h, method='PATCH', body=b)
        self.assertBody('key=val|body=patch request')