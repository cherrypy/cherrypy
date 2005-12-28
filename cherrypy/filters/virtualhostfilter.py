"""
Virtual Host Filter

From http://groups.google.com/group/cherrypy-users/browse_thread/thread/f393540fe278e54d:

For various reasons I need several domains to point to different parts of a
single website structure as well as to their own "homepage"   EG

http://www.mydom1.com  ->  root
http://www.mydom2.com  ->  root/mydom2/
http://www.mydom3.com  ->  root/mydom3/
http://www.mydom4.com  ->  under construction page

but also to have  http://www.mydom1.com/mydom2/  etc to be valid pages in
their own right.
"""

import cherrypy
from basefilter import BaseFilter


class VirtualHostFilter(BaseFilter):
    """Filter that changes the ObjectPath based on the Host.
    
    Useful when running multiple sites within one CP server.
    """
    
    def before_request_body(self):
        if not cherrypy.config.get('virtual_host_filter.on', False):
            return
        
        domain = cherrypy.request.headers.get('Host', '')
        if cherrypy.config.get("virtual_host_filter.use_x_forwarded_host", True):
            domain = cherrypy.request.headers.get("X-Forwarded-Host", domain)
        
        prefix = cherrypy.config.get("virtual_host_filter." + domain, "")
        if prefix:
            cherrypy.request.object_path = prefix + "/" + cherrypy.request.object_path

