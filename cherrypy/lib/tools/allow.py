import cherrypy


def allow(methods=None, debug=False):
    """Raise 405 if request.method not in methods (default ['GET', 'HEAD']).

    The given methods are case-insensitive, and may be in any order.
    If only one method is allowed, you may supply a single string;
    if more than one, supply a list of strings.

    Regardless of whether the current method is allowed or not, this
    also emits an 'Allow' response header, containing the given methods.
    """
    if not isinstance(methods, (tuple, list)):
        methods = [methods]
    methods = [m.upper() for m in methods if m]
    if not methods:
        methods = ['GET', 'HEAD']
    elif 'GET' in methods and 'HEAD' not in methods:
        methods.append('HEAD')

    cherrypy.response.headers['Allow'] = ', '.join(methods)
    if cherrypy.request.method not in methods:
        if debug:
            cherrypy.log('request.method %r not in methods %r' %
                         (cherrypy.request.method, methods), 'TOOLS.ALLOW')
        raise cherrypy.HTTPError(405)
    else:
        if debug:
            cherrypy.log('request.method %r in methods %r' %
                         (cherrypy.request.method, methods), 'TOOLS.ALLOW')
