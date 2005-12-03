import test
test.prefer_parent_path()

import xmlrpclib
import cherrypy

class Root:
    def index(self):
        return "I'm a standard index!"
    index.exposed = True


class XmlRpc:
    def return_single_item_list(self):
        return [42]
    return_single_item_list.exposed = True
    
    def return_string(self):
        return "here is a string"
    return_string.exposed = True
    
    def return_tuple(self):
        return ('here', 'is', 1, 'tuple')
    return_tuple.exposed = True
    
    def return_dict(self):
        return dict(a=1, b=2, c=3)
    return_dict.exposed = True
    
    def return_composite(self):
        return dict(a=1,z=26), 'hi', ['welcome', 'friend']
    return_composite.exposed = True

    def return_int(self):
        return 42
    return_int.exposed = True

    def return_float(self):
        return 3.14
    return_float.exposed = True

    def return_datetime(self):
        return xmlrpclib.DateTime((2003, 10, 7, 8, 1, 0, 1, 280, -1))
    return_datetime.exposed = True

    def return_boolean(self):
        return True
    return_boolean.exposed = True

    def test_argument_passing(self, num):
        return num * 2
    test_argument_passing.exposed = True

cherrypy.root = Root()
cherrypy.root.xmlrpc = XmlRpc()


import helper

cherrypy.config.update({
    'global': {'server.log_to_screen': False,
               'server.environment': 'production',
               'server.show_tracebacks': True,
               'server.socket_host': helper.CPWebCase.HOST,
               'server.socket_port': helper.CPWebCase.PORT,
               },
    '/xmlrpc': {'xmlrpc_filter.on':True},
    })


class ServerlessProxy(object):
    """An xmlrpc proxy for the test suite's 'serverless' tests."""
    def __init__(self, webcase, url):
        self._webcase = webcase
        self.url = url
    
    def __getattr__(self, attr, *args):
        def xmlrpc_method(*args):
            args = tuple(args)
            body = xmlrpclib.dumps(args, attr)
            cl = len(body)
            headers = [('Content-Type', 'text/xml'), ('Content-Length', str(cl))]
            self._webcase.getPage(self.url, headers=headers,
                                  method="POST", body=body)
            p, u = xmlrpclib.getparser()
            for line in self._webcase.body:
                p.feed(line)
            p.close()
            response = u.close()
            if len(response) == 1:
                response = response[0]
            return response
        return xmlrpc_method


class XmlRpcFilterTest(helper.CPWebCase):
    def testXmlRpcFilter(self):
        
        # load the appropriate xmlrpc proxy
        url = 'http://localhost:%s/xmlrpc/' % (self.PORT)
        if cherrypy.server.httpserver is None:
            proxy = ServerlessProxy(self, url)
        else:
            proxy = xmlrpclib.ServerProxy(url)
        
        # begin the tests ...
        self.assertEqual(proxy.return_single_item_list(), [42])
        self.assertNotEqual(proxy.return_single_item_list(), 'one bazillion')
        self.assertEqual(proxy.return_string(), "here is a string")
        self.assertEqual(proxy.return_tuple(), list(('here', 'is', 1, 'tuple')))
        self.assertEqual(proxy.return_dict(), {'a': 1, 'c': 3, 'b': 2})
        self.assertEqual(proxy.return_composite(),
                         [{'a': 1, 'z': 26}, 'hi', ['welcome', 'friend']])
        self.assertEqual(proxy.return_int(), 42)
        self.assertEqual(proxy.return_float(), 3.14)
        self.assertEqual(proxy.return_datetime(),
                         xmlrpclib.DateTime((2003, 10, 7, 8, 1, 0, 1, 280, -1)))
        self.assertEqual(proxy.return_boolean(), True)
        self.assertEqual(proxy.test_argument_passing(22), 22 * 2)
        
        # Test an error in the page handler (should raise an xmlrpclib.Fault)
        ignore = helper.webtest.ignored_exceptions
        ignore.append(TypeError)
        try:
            try:
                proxy.test_argument_passing({})
            except Exception, x:
                self.assertEqual(x.__class__, xmlrpclib.Fault)
                self.assertEqual(x.faultString, ("unsupported operand type(s) "
                                                 "for *: 'dict' and 'int'"))
            else:
                self.fail("Expected xmlrpclib.Fault")
        finally:
            ignore.pop()


if __name__ == '__main__':
    from cherrypy import _cpwsgi
    serverClass = _cpwsgi.WSGIServer
    helper.testmain(serverClass)

