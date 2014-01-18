import cherrypy
from cherrypy.lib.compat import json_encode


def json_handler(*args, **kwargs):
    value = cherrypy.serving.request._json_inner_handler(*args, **kwargs)
    return json_encode(value)


def json_out(content_type='application/json', debug=False,
             handler=json_handler):
    """Wrap request.handler to serialize its output to JSON. Sets Content-Type.

    If the given content_type is None, the Content-Type response header
    is not set.

    Provide your own handler to use a custom encoder.  For example
    cherrypy.config['tools.json_out.handler'] = <function>, or
    @json_out(handler=function).
    """
    request = cherrypy.serving.request
    # request.handler may be set to None by e.g. the caching tool
    # to signal to all components that a response body has already
    # been attached, in which case we don't need to wrap anything.
    if request.handler is None:
        return
    if debug:
        cherrypy.log('Replacing %s with JSON handler' % request.handler,
                     'TOOLS.JSON_OUT')
    request._json_inner_handler = request.handler
    request.handler = handler
    if content_type is not None:
        if debug:
            cherrypy.log('Setting Content-Type to %s' %
                         content_type, 'TOOLS.JSON_OUT')
        cherrypy.serving.response.headers['Content-Type'] = content_type
