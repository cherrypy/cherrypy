from hashlib import md5

import cherrypy
from cherrypy.lib import httputil as _httputil


def validate_etags(autotags=False, debug=False):
    """Validate the current ETag against If-Match, If-None-Match headers.

    If autotags is True, an ETag response-header value will be provided
    from an MD5 hash of the response body (unless some other code has
    already provided an ETag header). If False (the default), the ETag
    will not be automatic.

    WARNING: the autotags feature is not designed for URL's which allow
    methods other than GET. For example, if a POST to the same URL returns
    no content, the automatic ETag will be incorrect, breaking a fundamental
    use for entity tags in a possibly destructive fashion. Likewise, if you
    raise 304 Not Modified, the response body will be empty, the ETag hash
    will be incorrect, and your application will break.
    See :rfc:`2616` Section 14.24.
    """
    response = cherrypy.serving.response

    # Guard against being run twice.
    if hasattr(response, "ETag"):
        return

    status, reason, msg = _httputil.valid_status(response.status)

    etag = response.headers.get('ETag')

    # Automatic ETag generation. See warning in docstring.
    if etag:
        if debug:
            cherrypy.log('ETag already set: %s' % etag, 'TOOLS.ETAGS')
    elif not autotags:
        if debug:
            cherrypy.log('Autotags off', 'TOOLS.ETAGS')
    elif status != 200:
        if debug:
            cherrypy.log('Status not 200', 'TOOLS.ETAGS')
    else:
        etag = response.collapse_body()
        etag = '"%s"' % md5(etag).hexdigest()
        if debug:
            cherrypy.log('Setting ETag: %s' % etag, 'TOOLS.ETAGS')
        response.headers['ETag'] = etag

    response.ETag = etag

    # "If the request would, without the If-Match header field, result in
    # anything other than a 2xx or 412 status, then the If-Match header
    # MUST be ignored."
    if debug:
        cherrypy.log('Status: %s' % status, 'TOOLS.ETAGS')
    if 200 <= status <= 299:
        request = cherrypy.serving.request

        conditions = request.headers.elements('If-Match') or []
        conditions = [str(x) for x in conditions]
        if debug:
            cherrypy.log('If-Match conditions: %s' % repr(conditions),
                         'TOOLS.ETAGS')
        if conditions and not (conditions == ["*"] or etag in conditions):
            raise cherrypy.HTTPError(412, "If-Match failed: ETag %r did "
                                     "not match %r" % (etag, conditions))

        conditions = request.headers.elements('If-None-Match') or []
        conditions = [str(x) for x in conditions]
        if debug:
            cherrypy.log('If-None-Match conditions: %s' % repr(conditions),
                         'TOOLS.ETAGS')
        if conditions == ["*"] or etag in conditions:
            if debug:
                cherrypy.log('request.method: %s' %
                             request.method, 'TOOLS.ETAGS')
            if request.method in ("GET", "HEAD"):
                raise cherrypy.HTTPRedirect([], 304)
            else:
                raise cherrypy.HTTPError(412, "If-None-Match failed: ETag %r "
                                         "matched %r" % (etag, conditions))
