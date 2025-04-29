"""Encoding module."""
import struct
import time
import io

import cherrypy
from cherrypy._cpcompat import text_or_bytes
from cherrypy.lib import file_generator
from cherrypy.lib import is_closable_iterator
from cherrypy.lib import set_vary_header


_COMPRESSION_LEVEL_FAST = 1
_COMPRESSION_LEVEL_BEST = 9
_COMPRESSION_GZIP       = 'gzip'
_COMPRESSION_BROTLI     = 'br'
_COMPRESSION_ALL        = {_COMPRESSION_GZIP, _COMPRESSION_BROTLI}

_COMPRESSION_LEVEL_DEFAULTS = {
    'gzip': 5,
    'br': 4,
}


def decode(encoding=None, default_encoding='utf-8'):
    """Replace or extend the list of charsets used to decode a request entity.

    Either argument may be a single string or a list of strings.

    encoding
        If not None, restricts the set of charsets attempted while decoding
        a request entity to the given set (even if a different charset is
        given in the Content-Type request header).

    default_encoding
        Only in effect if the 'encoding' argument is not given.
        If given, the set of charsets attempted while decoding a request
        entity is *extended* with the given value(s).

    """
    body = cherrypy.request.body
    if encoding is not None:
        if not isinstance(encoding, list):
            encoding = [encoding]
        body.attempt_charsets = encoding
    elif default_encoding:
        if not isinstance(default_encoding, list):
            default_encoding = [default_encoding]
        body.attempt_charsets = body.attempt_charsets + default_encoding


class UTF8StreamEncoder:
    """UTF8 Stream Encoder."""

    def __init__(self, iterator):
        """Initialize a UTF-8 stream encoder instance."""
        self._iterator = iterator

    def __iter__(self):
        """Make a UTF-8-encoded stream iterator."""
        return self

    def next(self):
        """UTF-8-encode the next chunk of the stream."""
        return self.__next__()

    def __next__(self):
        """UTF-8-encode the next chunk of the stream."""
        res = next(self._iterator)
        if isinstance(res, str):
            res = res.encode('utf-8')
        return res

    def close(self):
        """Close the underlying byte stream."""
        if is_closable_iterator(self._iterator):
            self._iterator.close()

    def __getattr__(self, attr):
        """Return the underlying byte stream attribute value."""
        if attr.startswith('__'):
            raise AttributeError(self, attr)
        return getattr(self._iterator, attr)


class ResponseEncoder:
    """An HTTP response payload encoder."""

    default_encoding = 'utf-8'
    failmsg = 'Response body could not be encoded with %r.'
    encoding = None
    errors = 'strict'
    text_only = True
    add_charset = True
    debug = False

    def __init__(self, **kwargs):
        """Initialize HTTP response payload encoder."""
        for k, v in kwargs.items():
            setattr(self, k, v)

        self.attempted_charsets = set()
        request = cherrypy.serving.request
        if request.handler is not None:
            # Replace request.handler with self
            if self.debug:
                cherrypy.log('Replacing request.handler', 'TOOLS.ENCODE')
            self.oldhandler = request.handler
            request.handler = self

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
                if isinstance(chunk, str):
                    chunk = chunk.encode(encoding, self.errors)
                yield chunk
        self.body = encoder(self.body)
        return True

    def encode_string(self, encoding):
        """Encode a buffered response body."""
        if encoding in self.attempted_charsets:
            return False
        self.attempted_charsets.add(encoding)
        body = []
        for chunk in self.body:
            if isinstance(chunk, str):
                try:
                    chunk = chunk.encode(encoding, self.errors)
                except (LookupError, UnicodeError):
                    return False
            body.append(chunk)
        self.body = body
        return True

    def find_acceptable_charset(self):
        """Deduce acceptable charset for HTTP response."""
        request = cherrypy.serving.request
        response = cherrypy.serving.response

        if self.debug:
            cherrypy.log('response.stream %r' %
                         response.stream, 'TOOLS.ENCODE')
        if response.stream:
            encoder = self.encode_stream
        else:
            encoder = self.encode_string
            if 'Content-Length' in response.headers:
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
                del response.headers['Content-Length']

        # Parse the Accept-Charset request header, and try to provide one
        # of the requested charsets (in order of user preference).
        encs = request.headers.elements('Accept-Charset')
        charsets = [enc.value.lower() for enc in encs]
        if self.debug:
            cherrypy.log('charsets %s' % repr(charsets), 'TOOLS.ENCODE')

        if self.encoding is not None:
            # If specified, force this encoding to be used, or fail.
            encoding = self.encoding.lower()
            if self.debug:
                cherrypy.log('Specified encoding %r' %
                             encoding, 'TOOLS.ENCODE')
            if (not charsets) or '*' in charsets or encoding in charsets:
                if self.debug:
                    cherrypy.log('Attempting encoding %r' %
                                 encoding, 'TOOLS.ENCODE')
                if encoder(encoding):
                    return encoding
        else:
            if not encs:
                if self.debug:
                    cherrypy.log('Attempting default encoding %r' %
                                 self.default_encoding, 'TOOLS.ENCODE')
                # Any character-set is acceptable.
                if encoder(self.default_encoding):
                    return self.default_encoding
                else:
                    raise cherrypy.HTTPError(500, self.failmsg %
                                             self.default_encoding)
            else:
                for element in encs:
                    if element.qvalue > 0:
                        if element.value == '*':
                            # Matches any charset. Try our default.
                            if self.debug:
                                cherrypy.log('Attempting default encoding due '
                                             'to %r' % element, 'TOOLS.ENCODE')
                            if encoder(self.default_encoding):
                                return self.default_encoding
                        else:
                            encoding = element.value
                            if self.debug:
                                cherrypy.log('Attempting encoding %s (qvalue >'
                                             '0)' % element, 'TOOLS.ENCODE')
                            if encoder(encoding):
                                return encoding

                if '*' not in charsets:
                    # If no "*" is present in an Accept-Charset field, then all
                    # character sets not explicitly mentioned get a quality
                    # value of 0, except for ISO-8859-1, which gets a quality
                    # value of 1 if not explicitly mentioned.
                    iso = 'iso-8859-1'
                    if iso not in charsets:
                        if self.debug:
                            cherrypy.log('Attempting ISO-8859-1 encoding',
                                         'TOOLS.ENCODE')
                        if encoder(iso):
                            return iso

        # No suitable encoding found.
        ac = request.headers.get('Accept-Charset')
        if ac is None:
            msg = 'Your client did not send an Accept-Charset header.'
        else:
            msg = 'Your client sent this Accept-Charset header: %s.' % ac
        _charsets = ', '.join(sorted(self.attempted_charsets))
        msg += ' We tried these charsets: %s.' % (_charsets,)
        raise cherrypy.HTTPError(406, msg)

    def __call__(self, *args, **kwargs):
        """Set up encoding for the HTTP response."""
        response = cherrypy.serving.response
        self.body = self.oldhandler(*args, **kwargs)

        self.body = prepare_iter(self.body)

        ct = response.headers.elements('Content-Type')
        if self.debug:
            cherrypy.log('Content-Type: %r' % [str(h)
                         for h in ct], 'TOOLS.ENCODE')
        if ct and self.add_charset:
            ct = ct[0]
            if self.text_only:
                if ct.value.lower().startswith('text/'):
                    if self.debug:
                        cherrypy.log(
                            'Content-Type %s starts with "text/"' % ct,
                            'TOOLS.ENCODE')
                    do_find = True
                else:
                    if self.debug:
                        cherrypy.log('Not finding because Content-Type %s '
                                     'does not start with "text/"' % ct,
                                     'TOOLS.ENCODE')
                    do_find = False
            else:
                if self.debug:
                    cherrypy.log('Finding because not text_only',
                                 'TOOLS.ENCODE')
                do_find = True

            if do_find:
                # Set "charset=..." param on response Content-Type header
                ct.params['charset'] = self.find_acceptable_charset()
                if self.debug:
                    cherrypy.log('Setting Content-Type %s' % ct,
                                 'TOOLS.ENCODE')
                response.headers['Content-Type'] = str(ct)

        return self.body


def prepare_iter(value):
    """Ensure response body is iterable and resolves to False when empty."""
    if isinstance(value, text_or_bytes):
        # strings get wrapped in a list because iterating over a single
        # item list is much faster than iterating over every character
        # in a long string.
        if value:
            value = [value]
        else:
            # [''] doesn't evaluate to False, so replace it with [].
            value = []
    # Don't use isinstance here; io.IOBase which has an ABC takes
    # 1000 times as long as, say, isinstance(value, str)
    elif hasattr(value, 'read'):
        value = file_generator(value)
    elif value is None:
        value = []
    return value


# GZIP


def gzip_compress(body, compress_level):
    """Compress 'body' at the given compress_level."""
    import zlib

    # See https://tools.ietf.org/html/rfc1952
    yield b'\x1f\x8b'       # ID1 and ID2: gzip marker
    yield b'\x08'           # CM: compression method
    yield b'\x00'           # FLG: none set
    # MTIME: 4 bytes
    yield struct.pack('<L', int(time.time()) & int('FFFFFFFF', 16))

    # RFC 1952, section 2.3.1:
    #
    # XFL (eXtra FLags)
    #    These flags are available for use by specific compression
    #    methods.  The "deflate" method (CM = 8) sets these flags as
    #    follows:
    #
    #       XFL = 2 - compressor used maximum compression,
    #                 slowest algorithm
    #       XFL = 4 - compressor used fastest algorithm
    if compress_level == _COMPRESSION_LEVEL_BEST:
        yield b'\x02'       # XFL: max compression, slowest algo
    elif compress_level == _COMPRESSION_LEVEL_FAST:
        yield b'\x04'       # XFL: min compression, fastest algo
    else:
        yield b'\x00'       # XFL: compression unset/tradeoff
    yield b'\xff'           # OS: unknown

    crc = zlib.crc32(b'')
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
    yield struct.pack('<L', crc & int('FFFFFFFF', 16))
    # ISIZE: 4 bytes
    yield struct.pack('<L', size & int('FFFFFFFF', 16))


def decompress(body):
    """Decompress a blob of bytes."""
    import gzip

    zbuf = io.BytesIO()
    zbuf.write(body)
    zbuf.seek(0)
    zfile = gzip.GzipFile(mode='rb', fileobj=zbuf)
    data = zfile.read()
    zfile.close()
    return data


def gzip(compress_level=_COMPRESSION_LEVEL_DEFAULTS['gzip'],
        mime_types=['text/html', 'text/plain'], debug=False):
    """Try to gzip the response body if Content-Type in mime_types.

    cherrypy.response.headers['Content-Type'] must be set to one of the
    values in the mime_types arg before calling this function.

    The provided list of mime-types must be of one of the following form:
        * `type/subtype`
        * `type/*`
        * `type/*+subtype`

    No compression is performed if any of the following hold:
        * The client sends no Accept-Encoding request header
        * No 'gzip' or 'x-gzip' is present in the Accept-Encoding header
        * No 'gzip' or 'x-gzip' with a qvalue > 0 is present
        * The 'identity' value is given with a qvalue > 0.
    """
    request = cherrypy.serving.request
    response = cherrypy.serving.response

    apply_weighted_compression_method(request, response, 'TOOLS.GZIP',
        compress_level=compress_level, mime_types=mime_types, debug=debug)


# BROTLI

def apply_weighted_compression_method(request, response, context,
        compress_level=5, mime_types=['text/html', 'text/plain'], debug=False):
    """This function is called by the compression tools gzip and br (brotli).

    Try to compress the response based on the enabled tools (gzip/br) and
    also take into account the weigthed accepted encodings.

    No compression is performed if the response header already contains
    a content encoding of 'br' or 'gzip' to prevent compressing the content
    multiple times.

    Additionally no compression is performed if any of the following hold:
        * The client sends no Accept-Encoding request header
        * No accepted encoding is present in the Accept-Encoding header
        * No accepted encoding with a qvalue > 0 is present
        * The 'identity' value is given with a qvalue > 0.
    """
    set_vary_header(response, 'Accept-Encoding')

    if not response.body:
        # Response body is empty (might be a 304 for instance)
        if debug:
            cherrypy.log('No response body', context=context)
        return

    # If returning cached content (which should already have been compresses),
    # don't re-compress.
    if getattr(request, 'cached', False):
        if debug:
            cherrypy.log('Not compressing cached response', context=context)
        return

    ce = response.headers.get('Content-Encoding', '')
    if ce in _COMPRESSION_ALL:
        if debug:
            cherrypy.log('Content is already compressed', context=context)
        return None

    # Check which compression methods are enabled for the current path
    enabled_methods = set()
    toolmap = cherrypy.serving.request.toolmaps.get('tools', {})
    for name, settings in toolmap.items():
        if(name in _COMPRESSION_ALL) and settings.get('on', False):
            enabled_methods.add(name)
    if not enabled_methods:
        if debug:
            cherrypy.log('No compression tools configured', context=context)
        return None

    acceptable = request.headers.elements('Accept-Encoding')
    if not acceptable:
        # If no Accept-Encoding field is present in a request,
        # the server MAY assume that the client will accept any
        # content coding. In this case, if "identity" is one of
        # the available content-codings, then the server SHOULD use
        # the "identity" content-coding, unless it has additional
        # information that a different content-coding is meaningful
        # to the client.
        if debug:
            cherrypy.log('No Accept-Encoding', context=context)
        return None

    # Compile a list of compression method candidates
    # Do not use a set, we want to treat 'gzip' and 'x-gzip' differently
    candidates = []
    for coding in acceptable:
        if coding.value == 'identity' and coding.qvalue != 0:
            if debug:
                cherrypy.log('Non-zero identity qvalue: %s' % coding,
                             context=context)
            return None
        elif (coding.value in ('br', 'x-br')) and (_COMPRESSION_BROTLI in enabled_methods):
                candidates.append((coding.qvalue, _COMPRESSION_BROTLI))
        elif (coding.value in ('gzip', 'x-gzip')) and (_COMPRESSION_GZIP in enabled_methods):
            candidates.append((coding.qvalue, _COMPRESSION_GZIP))

    if(candidates):
        # get compression method from candidates
        # sort by weight (qvalue) descending, name ascending (to prefer 'br' over 'gzip')
        qvalue, cm = sorted(candidates, key=lambda x:(-x[0],x[1]))[0]
        if debug:
            cherrypy.log('Weighted Compression Method: %s' % cm, context=context)
        if qvalue == 0:
            if debug:
                cherrypy.log('Zero qvalue: %s' % cm, context=context)
            return
        ct = response.headers.get('Content-Type', '').split(';')[0]
        if ct not in mime_types:
            # If the list of provided mime-types contains tokens
            # such as 'text/*' or 'application/*+xml',
            # we go through them and find the most appropriate one
            # based on the given content-type.
            # The pattern matching is only caring about the most
            # common cases, as stated above, and doesn't support
            # for extra parameters.
            found = False
            if '/' in ct:
                ct_media_type, ct_sub_type = ct.split('/')
                for mime_type in mime_types:
                    if '/' in mime_type:
                        media_type, sub_type = mime_type.split('/')
                        if ct_media_type == media_type:
                            if sub_type == '*':
                                found = True
                                break
                            elif '+' in sub_type and '+' in ct_sub_type:
                                ct_left, ct_right = ct_sub_type.split('+')
                                left, right = sub_type.split('+')
                                if left == '*' and ct_right == right:
                                    found = True
                                    break

            if not found:
                if debug:
                    cherrypy.log('Content-Type %s not in mime_types %r' %
                                    (ct, mime_types), context=context)
                return

        # since we may be applying a different method than the one implied by
        # the caller we also must get the appropriate compression level
        cm_context = context.lower().split('.')[-1]
        if cm != cm_context:
            fallback = _COMPRESSION_LEVEL_DEFAULTS[cm]
            compress_level = toolmap[cm].get('compress_level', fallback)
        if debug:
            cherrypy.log('Compressing content. Method: %s / Level: %d' %
                            (cm, compress_level), context=context)
        # Return a generator that compresses the page
        response.headers['Content-Encoding'] = cm
        if cm == _COMPRESSION_BROTLI:
            response.body = brotli_compress(response.body, compress_level)
        elif cm == _COMPRESSION_GZIP:
            response.body = gzip_compress(response.body, compress_level)
        if 'Content-Length' in response.headers:
            # Delete Content-Length header so finalize() recalcs it.
            del response.headers['Content-Length']

        return

    if debug:
        cherrypy.log('No acceptable encoding found.', context=context)

    enabled_methods.add('identity')
    cherrypy.HTTPError(406, ', '.join(sorted(enabled_methods))).set_response()


def brotli_tool(compress_level=_COMPRESSION_LEVEL_DEFAULTS['br'],
        mime_types=['text/html', 'text/plain'], debug=False):
    """Try to brotli compress the response body if Content-Type in mime_types.

    cherrypy.response.headers['Content-Type'] must be set to one of the
    values in the mime_types arg before calling this function.

    The provided list of mime-types must be of one of the following form:
        * `type/subtype`
        * `type/*`
        * `type/*+subtype`

    No compression is performed if any of the following hold:
        * The client sends no Accept-Encoding request header
        * No 'br' or 'x-br' is present in the Accept-Encoding header
        * No 'br' or 'x-br' with a qvalue > 0 is present
        * The 'identity' value is given with a qvalue > 0.

    """
    request = cherrypy.serving.request
    response = cherrypy.serving.response

    apply_weighted_compression_method(request, response, 'TOOLS.BR',
        compress_level=compress_level, mime_types=mime_types, debug=debug)


def brotli_compress(body, compress_level):
    """Compress 'body' at the given compress_level."""
    import brotli

    for line in body:
        yield brotli.compress(line, quality=compress_level)
