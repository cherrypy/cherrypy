import cherrypy
from cherrypy.lib.compat import basestring, json_decode


def json_processor(entity):
    """Read application/json data into request.json."""
    if not entity.headers.get(u"Content-Length", u""):
        raise cherrypy.HTTPError(411)

    body = entity.fp.read()
    try:
        cherrypy.serving.request.json = json_decode(body.decode('utf-8'))
    except ValueError:
        raise cherrypy.HTTPError(400, 'Invalid JSON document')


def json_in(content_type=[u'application/json', u'text/javascript'],
            force=True, debug=False, processor=json_processor):
    """Add a processor to parse JSON request entities:
    The default processor places the parsed data into request.json.

    Incoming request entities which match the given content_type(s) will
    be deserialized from JSON to the Python equivalent, and the result
    stored at cherrypy.request.json. The 'content_type' argument may
    be a Content-Type string or a list of allowable Content-Type strings.

    If the 'force' argument is True (the default), then entities of other
    content types will not be allowed; "415 Unsupported Media Type" is
    raised instead.

    Supply your own processor to use a custom decoder, or to handle the parsed
    data differently.  The processor can be configured via
    tools.json_in.processor or via the decorator method.

    Note that the deserializer requires the client send a Content-Length
    request header, or it will raise "411 Length Required". If for any
    other reason the request entity cannot be deserialized from JSON,
    it will raise "400 Bad Request: Invalid JSON document".
    """
    request = cherrypy.serving.request
    if isinstance(content_type, basestring):
        content_type = [content_type]

    if force:
        if debug:
            cherrypy.log('Removing body processors %s' %
                         repr(request.body.processors.keys()), 'TOOLS.JSON_IN')
        request.body.processors.clear()
        request.body.default_proc = cherrypy.HTTPError(
            415, 'Expected an entity of content type %s' %
            ', '.join(content_type))

    for ct in content_type:
        if debug:
            cherrypy.log('Adding body processor for %s' % ct, 'TOOLS.JSON_IN')
        request.body.processors[ct] = processor
