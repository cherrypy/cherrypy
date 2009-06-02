try:
    set
except NameError:
    from sets import Set as set
import struct
import time
import types

import cherrypy
from cherrypy.lib import file_generator
from cherrypy.lib import set_vary_header


class ResponseEncoder:
    
    default_encoding = 'utf-8'
    failmsg = "Response body could not be encoded with %r."
    encoding = None
    errors = 'strict'
    text_only = True
    add_charset = True
    
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        
        self.attempted_charsets = set()
        
        if cherrypy.request.handler is not None:
            # Replace request.handler with self
            self.oldhandler = cherrypy.request.handler
            cherrypy.request.handler = self
    
    def encode_stream(self, encoding):
        """Encode a streaming response body.
        
        Use a generator wrapper, and just pray it works as the stream is
        being written out.
        """
        if encoding in self.attempted_charsets:
            return False
        self.attempted_charsets.add(encoding)
        
        def encoder(body):
            for chunk in body:
                if isinstance(chunk, unicode):
                    chunk = chunk.encode(encoding, self.errors)
                yield chunk
        self.body = encoder(self.body)
        return True
    
    def encode_string(self, encoding):
        """Encode a buffered response body."""
        if encoding in self.attempted_charsets:
            return False
        self.attempted_charsets.add(encoding)
        
        try:
            body = []
            for chunk in self.body:
                if isinstance(chunk, unicode):
                    chunk = chunk.encode(encoding, self.errors)
                body.append(chunk)
            self.body = body
        except (LookupError, UnicodeError):
            return False
        else:
            return True
    
    def find_acceptable_charset(self):
        response = cherrypy.response
        
        if cherrypy.response.stream:
            encoder = self.encode_stream
        else:
            encoder = self.encode_string
            if "Content-Length" in response.headers:
                # Delete Content-Length header so finalize() recalcs it.
                # Encoded strings may be of different lengths from their
                # unicode equivalents, and even from each other. For example:
                # >>> t = u"\u7007\u3040"
                # >>> len(t)
                # 2
                # >>> len(t.encode("UTF-8"))
                # 6
                # >>> len(t.encode("utf7"))
                # 8
                del response.headers["Content-Length"]
        
        # Parse the Accept-Charset request header, and try to provide one
        # of the requested charsets (in order of user preference).
        encs = cherrypy.request.headers.elements('Accept-Charset')
        charsets = [enc.value.lower() for enc in encs]
        
        if self.encoding is not None:
            # If specified, force this encoding to be used, or fail.
            encoding = self.encoding.lower()
            if (not charsets) or "*" in charsets or encoding in charsets:
                if encoder(encoding):
                    return encoding
        else:
            if not encs:
                # Any character-set is acceptable.
                if encoder(self.default_encoding):
                    return self.default_encoding
                else:
                    raise cherrypy.HTTPError(500, self.failmsg % self.default_encoding)
            else:
                if "*" not in charsets:
                    # If no "*" is present in an Accept-Charset field, then all
                    # character sets not explicitly mentioned get a quality
                    # value of 0, except for ISO-8859-1, which gets a quality
                    # value of 1 if not explicitly mentioned.
                    iso = 'iso-8859-1'
                    if iso not in charsets:
                        if encoder(iso):
                            return iso
                
                for element in encs:
                    if element.qvalue > 0:
                        if element.value == "*":
                            # Matches any charset. Try our default.
                            if encoder(self.default_encoding):
                                return self.default_encoding
                        else:
                            encoding = element.value
                            if encoder(encoding):
                                return encoding
        
        # No suitable encoding found.
        ac = cherrypy.request.headers.get('Accept-Charset')
        if ac is None:
            msg = "Your client did not send an Accept-Charset header."
        else:
            msg = "Your client sent this Accept-Charset header: %s." % ac
        msg += " We tried these charsets: %s." % ", ".join(self.attempted_charsets)
        raise cherrypy.HTTPError(406, msg)
    
    def __call__(self, *args, **kwargs):
        self.body = self.oldhandler(*args, **kwargs)
        
        if isinstance(self.body, basestring):
            # strings get wrapped in a list because iterating over a single
            # item list is much faster than iterating over every character
            # in a long string.
            if self.body:
                self.body = [self.body]
            else:
                # [''] doesn't evaluate to False, so replace it with [].
                self.body = []
        elif isinstance(self.body, types.FileType):
            self.body = file_generator(self.body)
        elif self.body is None:
            self.body = []
        
        ct = cherrypy.response.headers.elements("Content-Type")
        if ct:
            ct = ct[0]
            if (not self.text_only) or ct.value.lower().startswith("text/"):
                # Set "charset=..." param on response Content-Type header
                ct.params['charset'] = self.find_acceptable_charset()
                if self.add_charset:
                    cherrypy.response.headers["Content-Type"] = str(ct)
        
        return self.body

# GZIP

def compress(body, compress_level):
    """Compress 'body' at the given compress_level."""
    import zlib
    
    # See http://www.gzip.org/zlib/rfc-gzip.html
    yield '\x1f\x8b'       # ID1 and ID2: gzip marker
    yield '\x08'           # CM: compression method
    yield '\x00'           # FLG: none set
    # MTIME: 4 bytes
    yield struct.pack("<L", int(time.time()) & 0xFFFFFFFFL)
    yield '\x02'           # XFL: max compression, slowest algo
    yield '\xff'           # OS: unknown
    
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
    
    # CRC32: 4 bytes
    yield struct.pack("<L", crc & 0xFFFFFFFFL)
    # ISIZE: 4 bytes
    yield struct.pack("<L", size & 0xFFFFFFFFL)

def decompress(body):
    import gzip
    from cherrypy.py3util import StringIO
    
    zbuf = StringIO()
    zbuf.write(body)
    zbuf.seek(0)
    zfile = gzip.GzipFile(mode='rb', fileobj=zbuf)
    data = zfile.read()
    zfile.close()
    return data


def gzip(compress_level=5, mime_types=['text/html', 'text/plain']):
    """Try to gzip the response body if Content-Type in mime_types.
    
    cherrypy.response.headers['Content-Type'] must be set to one of the
    values in the mime_types arg before calling this function.
    
    No compression is performed if any of the following hold:
        * The client sends no Accept-Encoding request header
        * No 'gzip' or 'x-gzip' is present in the Accept-Encoding header
        * No 'gzip' or 'x-gzip' with a qvalue > 0 is present
        * The 'identity' value is given with a qvalue > 0.
    """
    response = cherrypy.response
    
    set_vary_header(response, "Accept-Encoding")
    
    if not response.body:
        # Response body is empty (might be a 304 for instance)
        return
    
    # If returning cached content (which should already have been gzipped),
    # don't re-zip.
    if getattr(cherrypy.request, "cached", False):
        return
    
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
    
    ct = response.headers.get('Content-Type', '').split(';')[0]
    for coding in acceptable:
        if coding.value == 'identity' and coding.qvalue != 0:
            return
        if coding.value in ('gzip', 'x-gzip'):
            if coding.qvalue == 0:
                return
            if ct in mime_types:
                # Return a generator that compresses the page
                response.headers['Content-Encoding'] = 'gzip'
                response.body = compress(response.body, compress_level)
                if "Content-Length" in response.headers:
                    # Delete Content-Length header so finalize() recalcs it.
                    del response.headers["Content-Length"]
            return
    cherrypy.HTTPError(406, "identity, gzip").set_response()

