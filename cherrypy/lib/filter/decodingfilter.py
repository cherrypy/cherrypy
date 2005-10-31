
from basefilter import BaseFilter

class DecodingFilter(BaseFilter):
    """Automatically decodes request parameters (except uploads)."""
    
    def beforeMain(self):
        # We have to dynamically import cherrypy because Python can't handle
        #   circular module imports :-(
        global cherrypy
        import cherrypy
        
        if not cherrypy.config.get('decodingFilter.on', False):
            return
        
        enc = cherrypy.config.get('decodingFilter.encoding', 'utf-8')
        for key, value in cherrypy.request.paramMap.items():
            if hasattr(value, 'file'):
                # This is a file being uploaded: skip it
                continue
            if isinstance(value, list):
                # value is a list: decode each element
                newValue = [v.decode(enc) for v in value]
            else:
                # value is a regular string: decode it
                newValue = value.decode(enc)
            cherrypy.request.paramMap[key] = newValue

