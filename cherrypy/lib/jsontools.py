import cherrypy

json_codecs = {}

def json_in(*args, **kwargs):
    if 'decoder' not in json_codecs:
        # we don't want to import simplejson until we're sure we need it
        from simplejson import JSONDecoder
        json_codecs['decoder'] = JSONDecoder()

    request = cherrypy.request
    _h = request.headers
    if ('Content-Type' not in _h
            or _h.elements('Content-Type')[0].value != 'application/json'):
        raise cherrypy.HTTPError(415, 'Expected an application/json content type')

    length = int(request.headers['Content-Length'])
    body = request.body.read(length)

    try:
        json = json_codecs['decoder'].decode(body)
    except ValueError:
        raise cherrypy.HTTPError(400, 'Invalid JSON document')

    request.json = json

def json_out(*args, **kwargs):
    if 'encoder' not in json_codecs:
        # we don't want to import simplejson until we're sure we need it
        from simplejson import JSONEncoder
        json_codecs['encoder'] = JSONEncoder()

    request = cherrypy.request
    response = cherrypy.response

    real_handler = request.handler
    def json_handler(*args, **kwargs):
        response.headers['Content-Type'] = 'application/json'
        value = real_handler(*args, **kwargs)
        return json_codecs['encoder'].iterencode(value)
    request.handler = json_handler
