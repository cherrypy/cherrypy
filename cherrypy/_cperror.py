"""Error classes for CherryPy."""

import urllib

class Error(Exception):
    pass

class NotReady(Error):
    """A request was made before the app server has been started."""
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
        request = cherrypy.request
        
        # Set a 'path' member attribute so that code which traps this
        # error can have access to it.
        self.path = path
        
        if params is not None:
            if isinstance(params, basestring):
                request.queryString = params
                pm = cgi.parse_qs(params, keep_blank_values=True)
                for key, val in pm.items():
                    if len(val) == 1:
                        pm[key] = val[0]
                request.paramMap = pm
            else:
                request.queryString = urllib.urlencode(params)
                request.paramMap = params.copy()
        
        Exception.__init__(self, path, params)



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
            # Note that any querystring in browserUrl will be discarded.
            url = urlparse.urljoin(cherrypy.request.browserUrl, url)
            abs_urls.append(url)
        self.urls = abs_urls
        
        # RFC 2616 indicates a 301 response code fits our goal; however,
        # browser support for 301 is quite messy. Do 302 instead. See
        # http://ppewww.ph.gla.ac.uk/~flavell/www/post-redirect.html
        if status is None:
            if cherrypy.response.version >= "1.1":
                status = 303
            else:
                status = 302
        else:
            status = int(status)
            if status < 300 or status > 399:
                raise ValueError("status must be between 300 and 399.")
        
        self.status = status
        Exception.__init__(self, abs_urls, status)
    
    def set_response(self):
        import cherrypy
        response = cherrypy.response
        response.status = status = self.status
        response.headerMap['Content-Type'] = "text/html"
        
        if status in (300, 301, 302, 303, 307):
            # "The ... URI SHOULD be given by the Location field
            # in the response."
            response.headerMap['Location'] = self.urls[0]
            
            # "Unless the request method was HEAD, the entity of the response
            # SHOULD contain a short hypertext note with a hyperlink to the
            # new URI(s)."
            msg = {300: "This resource can be found at <a href='%s'>%s</a>.",
                   301: "This resource has permanently moved to <a href='%s'>%s</a>.",
                   302: "This resource resides temporarily at <a href='%s'>%s</a>.",
                   303: "This resource can be found at <a href='%s'>%s</a>.",
                   307: "This resource has moved temporarily to <a href='%s'>%s</a>.",
                   }[status]
            response.body = "<br />\n".join([msg % (u, u) for u in self.urls])
        elif status == 304:
            # Not Modified.
            # "The response MUST include the following header fields:
            # Date, unless its omission is required by section 14.18.1"
            # The "Date" header should have been set in Request.__init__
            
            # "The 304 response MUST NOT contain a message-body."
            response.body = None
        elif status == 305:
            # Use Proxy.
            # self.urls[0] should be the URI of the proxy.
            response.headerMap['Location'] = self.urls[0]
            response.body = None
        else:
            raise ValueError("The %s status code is unknown." % status)


class HTTPError(Error):
    """ Exception used to return an HTTP error code to the client.
        This exception will automatically set the response status and body.
        
        A custom message (a long description to display in the browser)
        can be provided in place of the default.
    """
    
    def __init__(self, status=500, message=None):
        self.status = status = int(status)
        if status < 400 or status > 599:
            raise ValueError("status must be between 400 and 599.")
        self.message = message
        Error.__init__(self, status, message)
    
    def set_response(self):
        import cherrypy
        handler = cherrypy._cputil.getSpecialAttribute("_cpOnHTTPError")
        handler(self.status, self.message)


class NotFound(HTTPError):
    """ Happens when a URL couldn't be mapped to any class.method """
    
    def __init__(self, path=None):
        if path is None:
            import cherrypy
            path = cherrypy.request.path
        self.args = (path,)
        HTTPError.__init__(self, 404, "The path %s was not found." % repr(path))


class InternalError(HTTPError):
    """ Error that should never happen """
    
    def __init__(self, message=None):
        HTTPError.__init__(self, 500, message)

