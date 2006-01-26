import cherrypy
from basefilter import BaseFilter


class EncodingFilter(BaseFilter):
    """Filter that automatically encodes the response."""
    
    def before_finalize(self):
        conf = cherrypy.config.get
        if not conf('encoding_filter.on', False):
            return
        
        ct = cherrypy.response.headers.elements("Content-Type")
        if ct:
            ct = ct[0]
            if ct.value.lower().startswith("text/"):
                # Set "charset=..." param on response Content-Type header
                ct.params['charset'] = find_acceptable_charset()
                cherrypy.response.headers["Content-Type"] = str(ct)


def encode_stream(encoding):
    """Encode a streaming response body.
    
    Use a generator wrapper, and just pray it works as the stream is
    being written out.
    """
    def encoder(body):
        for line in body:
            yield line.encode(encoding)
    cherrypy.response.body = encoder(cherrypy.response.body)
    return True

def encode_string(encoding):
    """Encode a buffered response body."""
    try:
        body = []
        for chunk in cherrypy.response.body:
            body.append(chunk.encode(encoding))
        cherrypy.response.body = body
    except UnicodeError:
        return False
    else:
        return True

def find_acceptable_charset():
    conf = cherrypy.config.get
    response = cherrypy.response
    
    attempted_charsets = []
    
    stream = conf("stream_response", False)
    if stream:
        encode = encode_stream
    else:
        response.collapse_body()
        encode = encode_string
    
    failmsg = "The response could not be encoded with %s"
    
    enc = conf('encoding_filter.encoding', None)
    if enc is not None:
        # If specified, force this encoding to be used, or fail.
        if encode(enc):
            return enc
        else:
            raise cherrypy.HTTPError(500, failmsg % enc)
    
    # Parse the Accept_Charset request header, and try to provide one
    # of the requested charsets (in order of user preference).
    default_enc = conf('encoding_filter.default_encoding', 'utf-8')
    
    encs = cherrypy.request.headerMap.elements('Accept-Charset')
    if not encs:
        # Any character-set is acceptable.
        charsets = []
        if encode(default_enc):
            return default_enc
        else:
            raise cherrypy.HTTPError(500, failmsg % default_enc)
    else:
        charsets = [enc.value.lower() for enc in encs]
        if "*" not in charsets:
            # If no "*" is present in an Accept-Charset field, then all
            # character sets not explicitly mentioned get a quality
            # value of 0, except for ISO-8859-1, which gets a quality
            # value of 1 if not explicitly mentioned.
            iso = 'iso-8859-1'
            if iso not in charsets:
                attempted_charsets.append(iso)
                if encode(iso):
                    return iso
        
        for element in encs:
            if element.qvalue > 0:
                if element.value == "*":
                    # Matches any charset. Try our default.
                    if default_enc not in attempted_charsets:
                        attempted_charsets.append(default_enc)
                        if encode(default_enc):
                            return default_enc
                else:
                    encoding = element.value
                    if encoding not in attempted_charsets:
                        attempted_charsets.append(encoding)
                        if encode(encoding):
                            return encoding
    
    # No suitable encoding found.
    ac = cherrypy.request.headers.get('Accept-Charset')
    if ac is None:
        msg = "Your client did not send an Accept-Charset header."
    else:
        msg = "Your client sent this Accept-Charset header: %s." % ac
    msg += " We tried these charsets: %s." % ", ".join(attempted_charsets)
    raise cherrypy.HTTPError(406, msg)
