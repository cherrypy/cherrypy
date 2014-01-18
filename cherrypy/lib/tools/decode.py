import cherrypy


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
