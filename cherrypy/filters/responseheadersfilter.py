import cherrypy
from basefilter import BaseFilter

class ResponseHeadersFilter(BaseFilter):
    """Filter that allows HTTP headers to be defined for all responses"""

    def before_finalize(self):
        conf = cherrypy.config.get
        if not conf('response_headers_filter.on', False):
            return

        # headers must be a list of tuples
        headers = conf('response_headers_filter.headers', [])

        for item in headers:
            headername = item[0]
            headervalue = item[1]
            if headername not in cherrypy.response.headerMap:
                cherrypy.response.headerMap[headername] = headervalue
