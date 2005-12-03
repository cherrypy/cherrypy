import cherrypy
from basefilter import BaseFilter

class DecodingFilter(BaseFilter):
    """Automatically decodes request parameters (except uploads)."""
    
    def before_main(self):
        if not cherrypy.config.get('decoding_filter.on', False):
            return
        
        enc = cherrypy.config.get('decoding_filter.encoding', 'utf-8')
        for key, value in cherrypy.request.params.items():
            if hasattr(value, 'file'):
                # This is a file being uploaded: skip it
                continue
            if isinstance(value, list):
                # value is a list: decode each element
                newValue = [v.decode(enc) for v in value]
            else:
                # value is a regular string: decode it
                newValue = value.decode(enc)
            cherrypy.request.params[key] = newValue

