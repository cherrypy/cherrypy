import cherrypy


def redirect(url='', internal=True, debug=False):
    """Raise InternalRedirect or HTTPRedirect to the given url."""
    if debug:
        cherrypy.log('Redirecting %sto: %s' %
                     ({True: 'internal ', False: ''}[internal], url),
                     'TOOLS.REDIRECT')
    if internal:
        raise cherrypy.InternalRedirect(url)
    else:
        raise cherrypy.HTTPRedirect(url)
