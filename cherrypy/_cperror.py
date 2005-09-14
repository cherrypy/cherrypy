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

import urllib
import os


class Error(Exception):
    pass

class InternalError(Error):
    """ Error that should never happen """
    pass

class NotReady(Error):
    """A request was made before the app server has been started."""
    pass

class WrongResponseType(Error):
    """ Happens when the cherrypy.response.body is not a string """
    pass

class WrongUnreprValue(Error):
    """ Happens when unrepr can't parse a value """
    pass

class WrongConfigValue(Error):
    """ Happens when unrepr can't parse a config value """
    pass

class RequestHandled(Exception):
    """Exception raised when no further request handling should occur."""
    pass

class InternalRedirect(Exception):
    """Exception raised when processing should be handled by a different path.
    
    If you supply 'params', it will be used to re-populate paramMap.
    If 'params' is a dict, it will be used directly.
    If 'params' is a string, it will be converted to a dict using cgi.parse_qs.
    
    If you omit 'params', the paramMap from the original request will
    remain in effect, including any POST parameters.
    """
    
    def __init__(self, path, params=None):
        import cherrypy
        import cgi
        
        # Set a 'path' member attribute so that code which traps this
        # error can have access to it.
        self.path = path
        
        if params is not None:
            if isinstance(params, basestring):
                cherrypy.request.queryString = params
                pm = cgi.parse_qs(params, keep_blank_values=True)
                for key, val in pm.items():
                    if len(val) == 1:
                        pm[key] = val[0]
                cherrypy.request.paramMap = pm
            else:
                cherrypy.request.queryString = urllib.urlencode(params)
                cherrypy.request.paramMap = params.copy()
        
        cherrypy.request.browserUrl = cherrypy.request.base + path



class HTTPRedirect(Exception):
    """Exception raised when the request should be redirected.
    
    The new URL must be passed as the first argument to the Exception, e.g.,
        cperror.HTTPRedirect(newUrl). Multiple URLs are allowed. If a URL
        is absolute, it will be used as-is. If it is relative, it is assumed
        to be relative to the current cherrypy.request.path.
    """
    
    def __init__(self, urls, status=None):
        import urlparse
        import cherrypy
        
        if isinstance(urls, basestring):
            urls = [urls]
        
        abs_urls = []
        for url in urls:
            # Note that urljoin will "do the right thing" whether url is:
            #  1. a complete URL with host (e.g. "http://www.dummy.biz/test")
            #  2. a URL relative to root (e.g. "/dummy")
            #  3. a URL relative to the current path
            url = urlparse.urljoin(cherrypy.request.browserUrl, url)
            abs_urls.append(url)
        self.urls = abs_urls
        
        # RFC 2616 indicates a 301 response code fits our goal; however,
        # browser support for 301 is quite messy. Do 302 instead. See
        # http://ppewww.ph.gla.ac.uk/~flavell/www/post-redirect.html
        if status is None:
            if cherrypy.request.version >= "1.1":
                status = 303
            else:
                status = 302
        else:
            status = int(status)
            if status < 300 or status > 399:
                raise ValueError("status must be between 300 and 399.")
        
        self.status = status
    
    def set_response(self):
        import cherrypy
        cherrypy.response.status = status = self.status
        cherrypy.response.headerMap['Content-Type'] = "text/html"
        
        if status in (300, 301, 302, 303, 307):
            # "The ... URI SHOULD be given by the Location field
            # in the response."
            cherrypy.response.headerMap['Location'] = self.urls[0]
            
            # "Unless the request method was HEAD, the entity of the response
            # SHOULD contain a short hypertext note with a hyperlink to the
            # new URI(s)."
            msg = {300: "This resource can be found at <a href='%s'>%s</a>.",
                   301: "This resource has permanently moved to <a href='%s'>%s</a>.",
                   302: "This resource resides temporarily at <a href='%s'>%s</a>.",
                   303: "This resource can be found at <a href='%s'>%s</a>.",
                   307: "This resource has moved temporarily to <a href='%s'>%s</a>.",
                   }[status]
            cherrypy.response.body = "<br />\n".join([msg % (url, url)
                                                 for url in self.urls])
        elif status == 304:
            # Not Modified.
            # "The response MUST include the following header fields:
            # Date, unless its omission is required by section 14.18.1"
            # The "Date" header should have been set in Request.__init__
            
            # "The 304 response MUST NOT contain a message-body."
            cherrypy.response.body = []
        elif status == 305:
            # Use Proxy.
            # self.urls[0] should be the URI of the proxy.
            cherrypy.response.headerMap['Location'] = self.urls[0]
            cherrypy.response.body = []
        else:
            raise ValueError("The %s status code is unknown." % status)


_missing = object()

class HTTPError(Error):
    """ Exception used to return an HTTP error code to the client.
        This exception will automatically set the response status and body.
        
        A custom body can be pased to the init method in place of the
        standard error page.
    """
    
    def __init__(self, status=500, body=_missing):
        self.status = status = int(status)
        if status < 400 or status > 599:
            raise ValueError("status must be between 400 and 599.")
         
        self.body = body
    
    def set_response(self):
        import cherrypy
        
        # we now now have access to the traceback 
        statusString, defaultBody = cherrypy._cputil.getErrorStatusAndPage(self.status)
        
        if self.body is _missing:
            self.body = defaultBody
            # try to look up a custom error page in the config map
            # if there is no error page then use the pageGenerator
            
            # The page generator is used because the init method is called 
            # before the exception is raised.  It is impossible to embed the
            # traceback in the error page at this piont so we use the generator
            # to render the error page at a later point
            
            import cherrypy
            # try and read the page from a file
            # we use the default if the page can't be read
            try:
                errorPageFile = cherrypy.config.get('errorPage.%s' % status, '')
                self.body = file(errorPageFile, 'r')
            except:
                # we have alread set the body
                pass

        cherrypy.response.status = statusString
        cherrypy.response.body   = self.body
    
    def __str__(self):
        import cherrypy
        return cherrypy._cputil.getErrorStatusAndPage(self.status)[0]

class NotFound(HTTPError):
    """ Happens when a URL couldn't be mapped to any class.method """
    
    def __init__(self, path):
        self.args = (path,)
        HTTPError.__init__(self, 404)

    def __str__(self):
        return self.args[0]
