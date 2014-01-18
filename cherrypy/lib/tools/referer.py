"""Functions for builtin CherryPy tools."""

import re

import cherrypy


def referer(pattern, accept=True, accept_missing=False, error=403,
            message='Forbidden Referer header.', debug=False):
    """Raise HTTPError if Referer header does/does not match the given pattern.

    pattern
        A regular expression pattern to test against the Referer.

    accept
        If True, the Referer must match the pattern; if False,
        the Referer must NOT match the pattern.

    accept_missing
        If True, permit requests with no Referer header.

    error
        The HTTP error code to return to the client on failure.

    message
        A string to include in the response body on failure.

    """
    try:
        ref = cherrypy.serving.request.headers['Referer']
        match = bool(re.match(pattern, ref))
        if debug:
            cherrypy.log('Referer %r matches %r' % (ref, pattern),
                         'TOOLS.REFERER')
        if accept == match:
            return
    except KeyError:
        if debug:
            cherrypy.log('No Referer header', 'TOOLS.REFERER')
        if accept_missing:
            return

    raise cherrypy.HTTPError(error, message)
