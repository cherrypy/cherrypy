import cherrypy


def response_headers(headers=None, debug=False):
    """Set headers on the response."""
    if debug:
        cherrypy.log('Setting response headers: %s' % repr(headers),
                     'TOOLS.RESPONSE_HEADERS')
    for name, value in (headers or []):
        cherrypy.serving.response.headers[name] = value
response_headers.failsafe = True
