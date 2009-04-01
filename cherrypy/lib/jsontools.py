import cherrypy

try:
    # Python 2.6: simplejson is part of the standard library
    import json
except ImportError:
    try:
        import simplejson as json
    except ImportError:
        json = None

if json is None:
    def json_decode(s):
        raise ValueError('No JSON library is available')
    def json_encode(s):
        raise ValueError('No JSON library is available')
else:
    json_decode = json.JSONDecoder().decode
    json_encode = json.JSONEncoder().iterencode

def json_in(*args, **kwargs):
    request = cherrypy.request
    _h = request.headers
    if ('Content-Type' not in _h
            or _h.elements('Content-Type')[0].value != 'application/json'):
        raise cherrypy.HTTPError(415, 'Expected an application/json content type')

    length = int(request.headers['Content-Length'])
    body = request.body.read(length)

    try:
        json = json_decode(body)
    except ValueError:
        raise cherrypy.HTTPError(400, 'Invalid JSON document')

    request.json = json

def json_out(*args, **kwargs):
    request = cherrypy.request
    response = cherrypy.response

    real_handler = request.handler
    def json_handler(*args, **kwargs):
        response.headers['Content-Type'] = 'application/json'
        value = real_handler(*args, **kwargs)
        return json_encode(value)
    request.handler = json_handler
