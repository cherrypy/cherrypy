import cherrypy
from cherrypy._cpcompat import basestring


def accept(media=None, debug=False):
    """Return the client's preferred media-type (from the given Content-Types).

    If 'media' is None (the default), no test will be performed.

    If 'media' is provided, it should be the Content-Type value (as a string)
    or values (as a list or tuple of strings) which the current resource
    can emit. The client's acceptable media ranges (as declared in the
    Accept request header) will be matched in order to these Content-Type
    values; the first such string is returned. That is, the return value
    will always be one of the strings provided in the 'media' arg (or None
    if 'media' is None).

    If no match is found, then HTTPError 406 (Not Acceptable) is raised.
    Note that most web browsers send */* as a (low-quality) acceptable
    media range, which should match any Content-Type. In addition, "...if
    no Accept header field is present, then it is assumed that the client
    accepts all media types."

    Matching types are checked in order of client preference first,
    and then in the order of the given 'media' values.

    Note that this function does not honor accept-params (other than "q").
    """
    if not media:
        return
    if isinstance(media, basestring):
        media = [media]
    request = cherrypy.serving.request

    # Parse the Accept request header, and try to match one
    # of the requested media-ranges (in order of preference).
    ranges = request.headers.elements('Accept')
    if not ranges:
        # Any media type is acceptable.
        if debug:
            cherrypy.log('No Accept header elements', 'TOOLS.ACCEPT')
        return media[0]
    else:
        # Note that 'ranges' is sorted in order of preference
        for element in ranges:
            if element.qvalue > 0:
                if element.value == "*/*":
                    # Matches any type or subtype
                    if debug:
                        cherrypy.log('Match due to */*', 'TOOLS.ACCEPT')
                    return media[0]
                elif element.value.endswith("/*"):
                    # Matches any subtype
                    mtype = element.value[:-1]  # Keep the slash
                    for m in media:
                        if m.startswith(mtype):
                            if debug:
                                cherrypy.log('Match due to %s' % element.value,
                                             'TOOLS.ACCEPT')
                            return m
                else:
                    # Matches exact value
                    if element.value in media:
                        if debug:
                            cherrypy.log('Match due to %s' % element.value,
                                         'TOOLS.ACCEPT')
                        return element.value

    # No suitable media-range found.
    ah = request.headers.get('Accept')
    if ah is None:
        msg = "Your client did not send an Accept header."
    else:
        msg = "Your client sent this Accept header: %s." % ah
    msg += (" But this resource only emits these media types: %s." %
            ", ".join(media))
    raise cherrypy.HTTPError(406, msg)
