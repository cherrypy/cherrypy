"""
Copyright (c) 2004, CherryPy Team (team@cherrypy.org)
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, 
are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice, 
      this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice, 
      this list of conditions and the following disclaimer in the documentation 
      and/or other materials provided with the distribution.
    * Neither the name of the CherryPy Team nor the names of its contributors 
      may be used to endorse or promote products derived from this software 
      without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND 
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED 
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE 
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE 
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL 
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR 
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER 
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, 
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE 
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import xmlrpclib
from datetime import datetime
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

cherrypy.root = Root()
cherrypy.root.xmlrpc = XmlRpc()

cherrypy.config.update({
    'global': {'server.logToScreen': False,
               'server.environment': 'production',
               'server.showTracebacks': True,
               },
    '/xmlrpc':
               {'xmlRpcFilter.on':True}
              })

import helper

class XmlRpcFilterTest(helper.CPWebCase):
    def testXmlRpcFilter(self):
        proxy = xmlrpclib.ServerProxy('http://localhost:8080/xmlrpc/')

        self.assertEqual(proxy.return_single_item_list(),
                         [42]
                         )
        self.assertEqual(proxy.return_string(),
                         "here is a string"
                         )
        self.assertEqual(proxy.return_tuple(),
                         list(('here', 'is', 1, 'tuple'))
                         )
        self.assertEqual(proxy.return_dict(),
                         {'a': 1, 'c': 3, 'b': 2}
                         )
        self.assertEqual(proxy.return_composite(),
                         [{'a': 1, 'z': 26}, 'hi', ['welcome', 'friend']]
                         )
        self.assertEqual(proxy.return_int(),
                         42
                         )
        self.assertEqual(proxy.return_float(),
                               3.14
                        )
        self.assertEqual(proxy.return_datetime(),
                         xmlrpclib.DateTime((2003, 10, 7, 8, 1, 0, 1, 280, -1))
                         )
        self.assertEqual(proxy.return_boolean(),
                         True
                         )


if __name__ == '__main__':
    from cherrypy import _cpwsgi
    serverClass = _cpwsgi.WSGIServer
    helper.testmain(serverClass)
    