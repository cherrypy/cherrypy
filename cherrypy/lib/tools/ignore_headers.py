import cherrypy


def ignore_headers(headers=('Range',), debug=False):
    """Delete request headers whose field names are included in 'headers'.

    This is a useful tool for working behind certain HTTP servers;
    for example, Apache duplicates the work that CP does for 'Range'
    headers, and will doubly-truncate the response.
    """
    request = cherrypy.serving.request
    for name in headers:
        if name in request.headers:
            if debug:
                cherrypy.log('Ignoring request header %r' % name,
                             'TOOLS.IGNORE_HEADERS')
            del request.headers[name]
