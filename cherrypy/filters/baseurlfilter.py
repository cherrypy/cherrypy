import cherrypy
from basefilter import BaseFilter


class BaseUrlFilter(BaseFilter):
    """Filter that changes the base URL.
    
    Useful when running a CP server behind Apache.
    """
    
    def beforeRequestBody(self):
        if not cherrypy.config.get('baseUrlFilter.on', False):
            return
        
        request = cherrypy.request
        newBaseUrl = cherrypy.config.get('baseUrlFilter.baseUrl', 'http://localhost')
        if cherrypy.config.get('baseUrlFilter.useXForwardedHost', True):
            newBaseUrl = request.headerMap.get("X-Forwarded-Host", newBaseUrl)
        
        if newBaseUrl.find("://") == -1:
            # add http:// or https:// if needed
            newBaseUrl = request.base[:request.base.find("://") + 3] + newBaseUrl
        
        request.base = newBaseUrl
