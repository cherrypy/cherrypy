import cherrypy
from cherrypy.lib import set_vary_header
from cherrypy.lib.compression import compress


def gzip(compress_level=5, mime_types=['text/html', 'text/plain'],
         debug=False):
    """Try to gzip the response body if Content-Type in mime_types.

    cherrypy.response.headers['Content-Type'] must be set to one of the
    values in the mime_types arg before calling this function.

    The provided list of mime-types must be of one of the following form:
        * type/subtype
        * type/*
        * type/*+subtype

    No compression is performed if any of the following hold:
        * The client sends no Accept-Encoding request header
        * No 'gzip' or 'x-gzip' is present in the Accept-Encoding header
        * No 'gzip' or 'x-gzip' with a qvalue > 0 is present
        * The 'identity' value is given with a qvalue > 0.

    """
    request = cherrypy.serving.request
    response = cherrypy.serving.response

    set_vary_header(response, "Accept-Encoding")

    if not response.body:
        # Response body is empty (might be a 304 for instance)
        if debug:
            cherrypy.log('No response body', context='TOOLS.GZIP')
        return

    # If returning cached content (which should already have been gzipped),
    # don't re-zip.
    if getattr(request, "cached", False):
        if debug:
            cherrypy.log('Not gzipping cached response', context='TOOLS.GZIP')
        return

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
            cherrypy.log('No Accept-Encoding', context='TOOLS.GZIP')
        return

    ct = response.headers.get('Content-Type', '').split(';')[0]
    for coding in acceptable:
        if coding.value == 'identity' and coding.qvalue != 0:
            if debug:
                cherrypy.log('Non-zero identity qvalue: %s' % coding,
                             context='TOOLS.GZIP')
            return
        if coding.value in ('gzip', 'x-gzip'):
            if coding.qvalue == 0:
                if debug:
                    cherrypy.log('Zero gzip qvalue: %s' % coding,
                                 context='TOOLS.GZIP')
                return

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
                                     (ct, mime_types), context='TOOLS.GZIP')
                    return

            if debug:
                cherrypy.log('Gzipping', context='TOOLS.GZIP')
            # Return a generator that compresses the page
            response.headers['Content-Encoding'] = 'gzip'
            response.body = compress(response.body, compress_level)
            if "Content-Length" in response.headers:
                # Delete Content-Length header so finalize() recalcs it.
                del response.headers["Content-Length"]

            return

    if debug:
        cherrypy.log('No acceptable encoding found.', context='GZIP')
    cherrypy.HTTPError(406, "identity, gzip").set_response()
