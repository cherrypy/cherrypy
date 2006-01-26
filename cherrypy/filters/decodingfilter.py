import cherrypy
from basefilter import BaseFilter

class DecodingFilter(BaseFilter):
    """Automatically decodes request parameters (except uploads)."""
    
    def before_main(self):
        conf = cherrypy.config.get
        
        if not conf('decoding_filter.on', False):
            return
        
        enc = conf('decoding_filter.encoding', None)
        if not enc:
            ct = cherrypy.request.headers.elements("Content-Type")
            if ct:
                ct = ct[0]
                enc = ct.params.get("charset", None)
                if (not enc) and ct.value.lower().startswith("text/"):
                    # http://www.w3.org/Protocols/rfc2616/rfc2616-sec3.html#sec3.7.1
                    # When no explicit charset parameter is provided by the
                    # sender, media subtypes of the "text" type are defined
                    # to have a default charset value of "ISO-8859-1" when
                    # received via HTTP.
                    enc = "ISO-8859-1"
            
            if not enc:
                enc = conf('decoding_filter.default_encoding', "utf-8")
        
        try:
            self.decode(enc)
        except UnicodeDecodeError:
            # IE and Firefox don't supply a charset when submitting form
            # params with a CT of application/x-www-form-urlencoded.
            # So after all our guessing, it could *still* be wrong.
            # Start over with ISO-8859-1, since that seems to be preferred.
            self.decode("ISO-8859-1")
    
    def decode(self, enc):
        decodedParams = {}
        for key, value in cherrypy.request.params.items():
            if hasattr(value, 'file'):
                # This is a file being uploaded: skip it
                decodedParams[key] = value
            elif isinstance(value, list):
                # value is a list: decode each element
                decodedParams[key] = [v.decode(enc) for v in value]
            else:
                # value is a regular string: decode it
                decodedParams[key] = value.decode(enc)
        
        # Decode all or nothing, so we can try again on error.
        cherrypy.request.params = decodedParams

