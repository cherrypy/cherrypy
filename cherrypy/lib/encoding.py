import struct
import time

import cherrypy


def decode(encoding=None, default_encoding='utf-8'):
    """Decode cherrypy.request.params."""
    if not encoding:
        ct = cherrypy.request.headers.elements("Content-Type")
        if ct:
            ct = ct[0]
            encoding = ct.params.get("charset", None)
            if (not encoding) and ct.value.lower().startswith("text/"):
                # http://www.w3.org/Protocols/rfc2616/rfc2616-sec3.html#sec3.7.1
                # When no explicit charset parameter is provided by the
                # sender, media subtypes of the "text" type are defined
                # to have a default charset value of "ISO-8859-1" when
                # received via HTTP.
                encoding = "ISO-8859-1"
        
        if not encoding:
            encoding = default_encoding
    
    try:
        decode_params(encoding)
    except UnicodeDecodeError:
        # IE and Firefox don't supply a charset when submitting form
        # params with a CT of application/x-www-form-urlencoded.
        # So after all our guessing, it could *still* be wrong.
        # Start over with ISO-8859-1, since that seems to be preferred.
        decode_params("ISO-8859-1")

def decode_params(encoding):
    decoded_params = {}
    for key, value in cherrypy.request.params.items():
        if hasattr(value, 'file'):
            # This is a file being uploaded: skip it
            decoded_params[key] = value
        elif isinstance(value, list):
            # value is a list: decode each element
            decoded_params[key] = [v.decode(encoding) for v in value]
        else:
            # value is a regular string: decode it
            decoded_params[key] = value.decode(encoding)
    
    # Decode all or nothing, so we can try again on error.
    cherrypy.request.params = decoded_params


# Encoding

def encode(encoding=None, errors='strict'):
    # Guard against running twice
    if getattr(cherrypy.request, "_encoding_attempted", False):
        return
    cherrypy.request._encoding_attempted = True
    
    ct = cherrypy.response.headers.elements("Content-Type")
    if ct:
        ct = ct[0]
        if ct.value.lower().startswith("text/"):
            # Set "charset=..." param on response Content-Type header
            ct.params['charset'] = find_acceptable_charset(encoding, errors=errors)
            cherrypy.response.headers["Content-Type"] = str(ct)

def encode_stream(encoding, errors='strict'):
    """Encode a streaming response body.
    
    Use a generator wrapper, and just pray it works as the stream is
    being written out.
    """
    def encoder(body):
        for chunk in body:
            if isinstance(chunk, unicode):
                chunk = chunk.encode(encoding, errors)
            yield chunk
    cherrypy.response.body = encoder(cherrypy.response.body)
    return True

def encode_string(encoding, errors='strict'):
    """Encode a buffered response body."""
    try:
        body = []
        for chunk in cherrypy.response.body:
            if isinstance(chunk, unicode):
                chunk = chunk.encode(encoding, errors)
            body.append(chunk)
        cherrypy.response.body = body
    except (LookupError, UnicodeError):
        return False
    else:
        return True

def find_acceptable_charset(encoding=None, default_encoding='utf-8', errors='strict'):
    response = cherrypy.response
    
    if cherrypy.response.stream:
        encoder = encode_stream
    else:
        response.collapse_body()
        encoder = encode_string
    
    # Parse the Accept-Charset request header, and try to provide one
    # of the requested charsets (in order of user preference).
    encs = cherrypy.request.headers.elements('Accept-Charset')
    charsets = [enc.value.lower() for enc in encs]
    attempted_charsets = []
    
    if encoding is not None:
        # If specified, force this encoding to be used, or fail.
        encoding = encoding.lower()
        if (not charsets) or "*" in charsets or encoding in charsets:
            if encoder(encoding, errors):
                return encoding
    else:
        if not encs:
            # Any character-set is acceptable.
            if encoder(default_encoding, errors):
                return default_encoding
            else:
                raise cherrypy.HTTPError(500, failmsg % default_encoding)
        else:
            if "*" not in charsets:
                # If no "*" is present in an Accept-Charset field, then all
                # character sets not explicitly mentioned get a quality
                # value of 0, except for ISO-8859-1, which gets a quality
                # value of 1 if not explicitly mentioned.
                iso = 'iso-8859-1'
                if iso not in charsets:
                    attempted_charsets.append(iso)
                    if encoder(iso, errors):
                        return iso
            
            for element in encs:
                if element.qvalue > 0:
                    if element.value == "*":
                        # Matches any charset. Try our default.
                        if default_encoding not in attempted_charsets:
                            attempted_charsets.append(default_encoding)
                            if encoder(default_encoding, errors):
                                return default_encoding
                    else:
                        encoding = element.value
                        if encoding not in attempted_charsets:
                            attempted_charsets.append(encoding)
                            if encoder(encoding, errors):
                                return encoding
    
    # No suitable encoding found.
    ac = cherrypy.request.headers.get('Accept-Charset')
    if ac is None:
        msg = "Your client did not send an Accept-Charset header."
    else:
        msg = "Your client sent this Accept-Charset header: %s." % ac
    msg += " We tried these charsets: %s." % ", ".join(attempted_charsets)
    raise cherrypy.HTTPError(406, msg)


# GZIP

def compress(body, compress_level):
    """Compress 'body' at the given compress_level."""
    import zlib
    
    yield '\037\213'      # magic header
    yield '\010'         # compression method
    yield '\0'
    yield struct.pack("<L", long(time.time()))
    yield '\002'
    yield '\377'
    
    crc = zlib.crc32("")
    size = 0
    zobj = zlib.compressobj(compress_level,
                            zlib.DEFLATED, -zlib.MAX_WBITS,
                            zlib.DEF_MEM_LEVEL, 0)
    for line in body:
        size += len(line)
        crc = zlib.crc32(line, crc)
        yield zobj.compress(line)
    yield zobj.flush()
    yield struct.pack("<l", crc)
    yield struct.pack("<L", size & 0xFFFFFFFFL)

def gzip(compress_level=9, mime_types=['text/html', 'text/plain']):
    response = cherrypy.response
    if not response.body:
        # Response body is empty (might be a 304 for instance)
        return
    
    def zipit():
        # Return a generator that compresses the page
        varies = response.headers.get("Vary", "")
        varies = [x.strip() for x in varies.split(",") if x.strip()]
        if "Accept-Encoding" not in varies:
            varies.append("Accept-Encoding")
        response.headers['Vary'] = ", ".join(varies)
        
        response.headers['Content-Encoding'] = 'gzip'
        response.body = compress(response.body, compress_level)
    
    acceptable = cherrypy.request.headers.elements('Accept-Encoding')
    if not acceptable:
        # If no Accept-Encoding field is present in a request,
        # the server MAY assume that the client will accept any
        # content coding. In this case, if "identity" is one of
        # the available content-codings, then the server SHOULD use
        # the "identity" content-coding, unless it has additional
        # information that a different content-coding is meaningful
        # to the client.
        return
    
    ct = response.headers.get('Content-Type').split(';')[0]
    for coding in acceptable:
        if coding.value == 'identity' and coding.qvalue != 0:
            return
        if coding.value in ('gzip', 'x-gzip'):
            if coding.qvalue == 0:
                return
            if ct in mime_types:
                zipit()
            return
    cherrypy.HTTPError(406, "identity, gzip").set_response()
