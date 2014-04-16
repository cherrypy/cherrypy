import cherrypy
from cherrypy.lib.compat import basestring, unicodestr
from cherrypy.lib import file_generator


class UTF8StreamEncoder:
    def __init__(self, iterator):
        self._iterator = iterator

    def __iter__(self):
        return self

    def next(self):
        return self.__next__()

    def __next__(self):
        res = next(self._iterator)
        if isinstance(res, unicodestr):
            res = res.encode('utf-8')
        return res

    def __getattr__(self, attr):
        if attr.startswith('__'):
            raise AttributeError(self, attr)
        return getattr(self._iterator, attr)


class ResponseEncoder:

    default_encoding = 'utf-8'
    failmsg = "Response body could not be encoded with %r."
    encoding = None
    errors = 'strict'
    text_only = True
    add_charset = True
    debug = False

    def __init__(self, **kwargs):
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
                if isinstance(chunk, unicodestr):
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
            if isinstance(chunk, unicodestr):
                try:
                    chunk = chunk.encode(encoding, self.errors)
                except (LookupError, UnicodeError):
                    return False
            body.append(chunk)
        self.body = body
        return True

    def find_acceptable_charset(self):
        request = cherrypy.serving.request
        response = cherrypy.serving.response

        if self.debug:
            cherrypy.log('response.stream %r' %
                         response.stream, 'TOOLS.ENCODE')
        if response.stream:
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
            if (not charsets) or "*" in charsets or encoding in charsets:
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
                        if element.value == "*":
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

                if "*" not in charsets:
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
            msg = "Your client did not send an Accept-Charset header."
        else:
            msg = "Your client sent this Accept-Charset header: %s." % ac
        _charsets = ", ".join(sorted(self.attempted_charsets))
        msg += " We tried these charsets: %s." % (_charsets,)
        raise cherrypy.HTTPError(406, msg)

    def __call__(self, *args, **kwargs):
        response = cherrypy.serving.response
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
        elif hasattr(self.body, 'read'):
            self.body = file_generator(self.body)
        elif self.body is None:
            self.body = []

        ct = response.headers.elements("Content-Type")
        if self.debug:
            cherrypy.log('Content-Type: %r' % [str(h)
                         for h in ct], 'TOOLS.ENCODE')
        if ct and self.add_charset:
            ct = ct[0]
            if self.text_only:
                if ct.value.lower().startswith("text/"):
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
                response.headers["Content-Type"] = str(ct)

        return self.body
