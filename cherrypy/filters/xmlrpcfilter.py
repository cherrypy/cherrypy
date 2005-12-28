##########################################################################
## Remco Boerma
## Sylvain Hellegouarch
##
## History:
## 1.0.6   : 2005-12-04 Fixed error handling problems
## 1.0.5   : 2005-11-04 Fixed Content-Length bug (http://www.cherrypy.org/ticket/384)
## 1.0.4   : 2005-08-28 Fixed issues on input types which are not strings
## 1.0.3   : 2005-01-28 Bugfix on content-length in 1.0.2 code fixed by
##           Gian Paolo Ciceri
## 1.0.2   : 2005-01-26 changed infile dox based on ticket #97
## 1.0.1   : 2005-01-26 Speedup due to generator usage in CP2.
##           The result is now converted to a list with length 1. So the complete
##           xmlrpc result is written at once, and not per character. Thanks to
##           Gian Paolo Ciceri for reporting the slowdown.
## 1.0.0   : 2004-12-29 Released with CP2
## 0.0.9   : 2004-12-23 made it CP2 #59 compatible (returns an iterable)
##           Please note: as the xmlrpc doesn't know what you would want to return
##           (and for the logic of marshalling) it will return Generator objects, as
##           it is.. So it'll brake on that one!!
##           NOTE: __don't try to return a Generator object to the caller__
##           You could of course handle the generator usage internally, before sending
##           the result. This breaks from the general cherrypy way of handling generators...
## 0.0.8   : 2004-12-23 cherrypy.request.paramList should now be a filter. 
## 0.0.7   : 2004-12-07 inserted in the experimental branch (all remco boerma till here)
## 0.0.6   : 2004-12-02 Converted basefilter to baseinputfileter,baseoutputfilter
## 0.0.5   : 2004-11-22 "RPC2/" now changed to "/RPC2/" with the new mapping function
##           Gian paolo ciceri notified me with the lack of passing parameters.
##           Thanks Gian, it's now implemented against the latest trunk.
##           Gian also came up with the idea of lazy content-type checking: if it's sent
##           as a header, it should be 'text/xml', if not sent at all, it should be
##           accepted. (While this it not the xml/rpc standard, it's handy for those
##           xml-rpc client implementations wich don't send this header)
## 0.0.4   : 2004-11-20 in setting the path, the dot is replaces by a slash
##           therefore the regular CP2 routines knows how to handle things, as 
##           dots are not allowed in object names, it's varely easily adopted. 
##           Path + method handling. The default path is 'RPC2', this one is 
##           stripped. In case of path 'someurl' it is used for 'someurl' + method
##           and 'someurl/someotherurl' is mapped to someurl.someotherurl + method.
##           this way python serverproxies initialised with an url other than 
##           just the host are handled well. I don't hope any other service would map
##           it to 'RPC2/someurl/someotherurl', cause then it would break i think. .
## 0.0.3   : 2004-11-19 changed some examples (includes error checking 
##           wich returns marshalled Fault objects if the request is an RPC call.
##           took testing code form afterRequestHeader and put it in 
##           testValidityOfRequest to make things a little simpler. 
##           simply log the requested function with parameters to stdout
## 0.0.2   : 2004-11-19 the required cgi.py patch is no longer needed
##           (thanks remi for noticing). Webbased calls to regular objects
##           are now possible again ;) so it's no longer a dedicated xmlrpc
##           server. The test script is also in a ready to run file named 
##           testRPC.py along with the test server: filterExample.py
## 0.0.1   : 2004-11-19 informing the public, dropping loads of useless
##           tests and debugging
## 0.0.0   : 2004-11-19 initial alpha
## 
##---------------------------------------------------------------------
## 
## EXAMPLE CODE FOR THE SERVER:
##    import cherrypy
##
##    class Root:
##        def longString(self, s, times):
##            return s * times
##        longString.exposed = True
##
##    cherrypy.root = Root()
##    cherrypy.config.update({'xmlrpc_filter.on': True,
##                            'socket_port': 9001,
##                            'thread_pool':0,
##                            'socket_queue_size':10 })
##    if __name__=='__main__':
##        cherrypy.server.start()
##
## EXAMPLE CODE FOR THE CLIENT:
## >>> import xmlrpclib
## >>> server = xmlrpclib.ServerProxy('http://localhost:9001')
## >>> assert server.longString('abc', 3) == 'abcabcabc'
## >>>
######################################################################


import sys
import xmlrpclib

import cherrypy
from basefilter import BaseFilter


class XmlRpcFilter(BaseFilter):
    """Converts XMLRPC to CherryPy2 object system and vice-versa.
    
    PLEASE NOTE:
    
    before_request_body:
        Unmarshalls the posted data to a methodname and parameters.
        - These are stored in cherrypy.request.rpcMethod and .rpcParams
        - The method is also stored in cherrypy.request.object_path,
          so CP2 will find the right method to call for you,
          based on the root's position.
    before_main:
        Marshalls cherrypy.response.body to xmlrpc.
        - Until resolved: cherrypy.response.body must be a python source string;
          this string is 'eval'ed to return the results. This will be
          resolved in the future.
        - Content-Type and Content-Length are set according to the new
          (marshalled) data.
    """
    
    def testValidityOfRequest(self):
        # test if the content-length was sent
        length = cherrypy.request.headers.get('Content-Length') or 0
        ct = cherrypy.request.headers.get('Content-Type') or 'text/xml'
        return int(length) > 0 and ct.lower() in ['text/xml']
    
    def before_request_body(self):
        """ Called after the request header has been read/parsed"""
        request = cherrypy.request
        
        request.xmlrpc_filter_on = cherrypy.config.get('xmlrpc_filter.on', False)
        if not request.xmlrpc_filter_on:
            return
        
        request.is_rpc = self.testValidityOfRequest()
        if not request.is_rpc: 
            return
        
        request.processRequestBody = False
        dataLength = int(request.headers.get('Content-Length') or 0)
        data = request.rfile.read(dataLength)
        try:
            params, method = xmlrpclib.loads(data)
        except Exception:
            params, method = ('ERROR PARAMS', ), 'ERRORMETHOD'
        request.rpcMethod, request.rpcParams = method, params
        
        # patch the path. there are only a few options:
        # - 'RPC2' + method >> method
        # - 'someurl' + method >> someurl.method
        # - 'someurl/someother' + method >> someurl.someother.method
        if not request.object_path.endswith('/'):
            request.object_path += '/'
        if request.object_path.startswith('/RPC2/'):
            # strip the first /rpc2
            request.object_path = request.object_path[5:]
        request.object_path += str(method).replace('.', '/')
        request.paramList = list(params)
    
    def before_main(self):
        """This is a variation of main() from _cphttptools.
        
        It is redone here because:
            1. we want to handle responses of any type
            2. we need to pass our own paramList
        """
        
        if (not cherrypy.config.get('xmlrpc_filter.on', False)
            or not getattr(cherrypy.request, 'is_rpc', False)):
            return
        
        path = cherrypy.request.object_path
        while True:
            try:
                page_handler, object_path, virtual_path = cherrypy.request.mapPathToObject(path)
                
                # Decode any leftover %2F in the virtual_path atoms.
                virtual_path = [x.replace("%2F", "/") for x in virtual_path]
                
                # Remove "root" from object_path and join it to get object_path
                self.object_path = '/' + '/'.join(object_path[1:])
                args = virtual_path + cherrypy.request.paramList
                body = page_handler(*args, **cherrypy.request.params)
                break
            except cherrypy.InternalRedirect, x:
                # Try again with the new path
                path = x.path
        
        # See xmlrpclib documentation
        # Python's None value cannot be used in standard XML-RPC;
        # to allow using it via an extension, provide a true value for allow_none.
        encoding = cherrypy.config.get('xmlrpc_filter.encoding', 'utf-8')
        body = xmlrpclib.dumps((body,), methodresponse=1,
                               encoding=encoding, allow_none=0)
        self.respond(body)
        cherrypy.request.execute_main = False
    
    def after_error_response(self):
        if (not cherrypy.config.get('xmlrpc_filter.on', False)
            or not getattr(cherrypy.request, 'is_rpc', False)):
            return
        
        # Since we got here because of an exception,
        # let's get its error message if any
        body = str(sys.exc_info()[1])
        body = xmlrpclib.dumps(xmlrpclib.Fault(1, body))
        self.respond(body)
    
    def respond(self, body):
        # The XML-RPC spec (http://www.xmlrpc.com/spec) says:
        # "Unless there's a lower-level error, always return 200 OK."
        # Since Python's xmlrpclib interprets a non-200 response
        # as a "Protocol Error", we'll just return 200 every time.
        response = cherrypy.response
        response.status = '200 OK'
        response.body = body
        response.headers['Content-Type'] = 'text/xml'
        response.headers['Content-Length'] = len(body)

