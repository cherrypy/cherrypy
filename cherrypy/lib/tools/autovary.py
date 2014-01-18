import cherrypy
from cherrypy.lib import httputil as _httputil


class MonitoredHeaderMap(_httputil.HeaderMap):

    def __init__(self):
        self.accessed_headers = set()

    def __getitem__(self, key):
        self.accessed_headers.add(key)
        return _httputil.HeaderMap.__getitem__(self, key)

    def __contains__(self, key):
        self.accessed_headers.add(key)
        return _httputil.HeaderMap.__contains__(self, key)

    def get(self, key, default=None):
        self.accessed_headers.add(key)
        return _httputil.HeaderMap.get(self, key, default=default)

    if hasattr({}, 'has_key'):
        # Python 2
        def has_key(self, key):
            self.accessed_headers.add(key)
            return _httputil.HeaderMap.has_key(self, key)


def autovary(ignore=None, debug=False):
    """Auto-populate the Vary response header based on request.header access.
    """
    request = cherrypy.serving.request

    req_h = request.headers
    request.headers = MonitoredHeaderMap()
    request.headers.update(req_h)
    if ignore is None:
        ignore = set(['Content-Disposition', 'Content-Length', 'Content-Type'])

    def set_response_header():
        resp_h = cherrypy.serving.response.headers
        v = set([e.value for e in resp_h.elements('Vary')])
        if debug:
            cherrypy.log(
                'Accessed headers: %s' % request.headers.accessed_headers,
                'TOOLS.AUTOVARY')
        v = v.union(request.headers.accessed_headers)
        v = v.difference(ignore)
        v = list(v)
        v.sort()
        resp_h['Vary'] = ', '.join(v)
    request.hooks.attach('before_finalize', set_response_header, 95)
