import cherrypy
from basefilter import BaseFilter


class EncodingFilter(BaseFilter):
    """Filter that automatically encodes the response."""
    
    def find_acceptable_charset(self):
        conf = cherrypy.config.get
        response = cherrypy.response
        
        stream = conf("streamResponse", False)
        if stream:
            # Use a generator wrapper, and just pray it works as the
            # stream is being written out.
            def encode_body(encoding):
                def encoder(body):
                    for line in body:
                        yield line.encode(encoding)
                response.body = encoder(response.body)
                return True
        else:
            response.body = ''.join([chunk for chunk in response.body])
            def encode_body(encoding):
                try:
                    response.body = response.body.encode(encoding)
                except UnicodeError:
                    # Try the next encoding
                    return False
                else:
                    return True
        
        failmsg = "The response could not be encoded with %s"
        
        enc = conf('encodingFilter.encoding', None)
        if enc is not None:
            # If specified, force this encoding to be used, or fail.
            if encode_body(enc):
                return enc
            else:
                raise cherrypy.HTTPError(500, failmsg % enc)
        
        # Parse the Accept_Charset request header, and try to provide one
        # of the requested charsets (in order of user preference).
        default_enc = conf('encodingFilter.defaultEncoding', 'utf-8')
        
        encs = cherrypy.request.headerMap.elements('Accept-Charset')
        if encs is None:
            # Any character-set is acceptable.
            if encode_body(default_enc):
                return default_enc
            else:
                raise cherrypy.HTTPError(500, failmsg % default_enc)
        else:
            newbody = None
            charsets = [enc.value.lower() for enc in encs]
            if "*" not in charsets:
                # If no "*" is present in an Accept-Charset field, then all
                # character sets not explicitly mentioned get a quality
                # value of 0, except for ISO-8859-1, which gets a quality
                # value of 1 if not explicitly mentioned.
                iso = 'iso-8859-1'
                if iso not in charsets:
                    if encode_body(iso):
                        return iso
            
            for element in encs:
                if element.qvalue > 0:
                    if element.value == "*":
                        # Matches any charset. Try our default.
                        if encode_body(default_enc):
                            return default_enc
                    else:
                        if encode_body(element.value):
                            return element.value
        
        # No suitable encoding found.
        raise cherrypy.HTTPError(406)
    
    def beforeFinalize(self):
        conf = cherrypy.config.get
        if not conf('encodingFilter.on', False):
            return
        
        ct = cherrypy.response.headerMap.elements("Content-Type")
        if ct is not None:
            ct = ct[0]
            if ct.value.lower().startswith("text/"):
                # Set "charset=..." param on response Content-Type header
                ct.params['charset'] = self.find_acceptable_charset()
                cherrypy.response.headerMap["Content-Type"] = str(ct)

