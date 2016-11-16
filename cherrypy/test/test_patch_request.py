"""Simple test for HTTP PATCH requests."""

import cherrypy
from cherrypy.test import helper
from pprint import pprint

class PatchRequestTests(helper.CPWebCase):

    @staticmethod
    def setup_server():
        """Sets up a basic cherryPy server for testing.
        """

        class Root(object):

            @cherrypy.expose
            def patch(self, param):
                """Makes sure that PATCH requests work

                Args:
                    kwargs (dict): values passed in the URI and body

                Returns:
                    str: the values from the URI and body
                """
                print('[LOG] in PATCH method')
                data = cherrypy.request.body.read()

                print('[LOG] data is: ')
                print(data)
                print('[LOG] query param is: ')
                print(param)

                res = 'param=' + param + '|body='
                retVal = str.encode(res, 'utf-8') + data

                print(retVal)
                return retVal

        root = Root()
        
        conf = {
            '/': {
                'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            }
        }

        cherrypy.tree.mount(root, '/root')


    def test_HttpPatchMethod(self):
        b = 'patch request'
        h = [('Content-Type', 'text/plain'),
             ('Content-Length', str(len(b)))]
        self.getPage('/root/patch?param=val', headers=h, method='PATCH', body=b)
        self.assertBody('param=val|body=patch request')
