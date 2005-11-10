
from basefilter import BaseFilter

class EncodingFilter(BaseFilter):
    """Filter that automatically encodes the response."""
    
    def beforeFinalize(self):
        # We have to dynamically import cherrypy because Python can't handle
        #   circular module imports :-(
        global cherrypy
        import cherrypy
        
        conf = cherrypy.config.get
        if not conf('encodingFilter.on', False):
            return
        
        contentType = cherrypy.response.headerMap.get("Content-Type")
        if contentType:
            ctlist = contentType.split(';')[0]
            if (ctlist in conf('encodingFilter.mimeTypeList', ['text/html'])):
                enc = conf('encodingFilter.encoding', 'utf-8')
                
                # Add "charset=..." to response Content-Type header
                if contentType and 'charset' not in contentType:
                    cherrypy.response.headerMap["Content-Type"] += ";charset=%s" % enc
                
                # Return a generator that encodes the sequence
                def encode_body(body):
                    for line in body:
                        yield line.encode(enc)
                cherrypy.response.body = encode_body(cherrypy.response.body)
