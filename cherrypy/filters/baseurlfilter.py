import cherrypy
from basefilter import BaseFilter


class BaseUrlFilter(BaseFilter):
    """Filter that changes the base URL.
    
    Useful when running a CP server behind Apache.
    """
    
    def before_request_body(self):
        if not cherrypy.config.get('base_url_filter.on', False):
            return
        
        request = cherrypy.request
        newBaseUrl = cherrypy.config.get('base_url_filter.base_url', 'http://localhost')
        if cherrypy.config.get('base_url_filter.use_x_forwarded_host', True):
            newBaseUrl = request.headers.get("X-Forwarded-Host", newBaseUrl)
        
        if newBaseUrl.find("://") == -1:
            # add http:// or https:// if needed
            newBaseUrl = request.base[:request.base.find("://") + 3] + newBaseUrl
        
        request.base = newBaseUrl
