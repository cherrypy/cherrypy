import cherrypy


def trailing_slash(missing=True, extra=False, status=None, debug=False):
    """Redirect if path_info has (missing|extra) trailing slash."""
    request = cherrypy.serving.request
    pi = request.path_info

    if debug:
        cherrypy.log('is_index: %r, missing: %r, extra: %r, path_info: %r' %
                     (request.is_index, missing, extra, pi),
                     'TOOLS.TRAILING_SLASH')
    if request.is_index is True:
        if missing:
            if not pi.endswith('/'):
                new_url = cherrypy.url(pi + '/', request.query_string)
                raise cherrypy.HTTPRedirect(new_url, status=status or 301)
    elif request.is_index is False:
        if extra:
            # If pi == '/', don't redirect to ''!
            if pi.endswith('/') and pi != '/':
                new_url = cherrypy.url(pi[:-1], request.query_string)
                raise cherrypy.HTTPRedirect(new_url, status=status or 301)
