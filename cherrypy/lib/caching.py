import datetime
import threading
import time

import cherrypy
from cherrypy.lib import cptools, httputil

class VaryHeaderAwareStore:
    """
    A cache store that honors the Vary headers and keeps
    a separate cached copy for each.
    """
    def __init__(self):
        # keep a nested dictionary of cached responses indexed first by
        #  URI and then by "Vary" header values
        self.uri_store = {}
    
    def get_key_from_request(self, request, response=None):
        """The key into the index needs to be some combination of
        the URI and the request headers indicated by the response
        as Varying in a normalized (e.g. sorted) format."""
        # First, get a cached response for the URI
        uri = VaryHeaderUnawareStore.get_key_from_request(request)
        try:
            # Try to get the cached response from the uri
            cached_resp = self._get_any_response(uri)
            response_headers = cached_resp[1]
        except KeyError:
            # if the cached response isn't available, use the immediate
            #  response
            response_headers = response.headers
        vary_header_values = self._get_vary_header_values(request, response_headers)
        return uri, '|'.join(vary_header_values)

    def _get_vary_header_values(request, response_headers):
        h = response_headers
        vary_header_names = [e.value for e in h.elements('Vary')]
        vary_header_names.sort()
        vary_header_values = [
            request.headers.get(h_name, '')
            for h_name in vary_header_names]
        return vary_header_values
    _get_vary_header_values = staticmethod(_get_vary_header_values)

    def _get_any_response(self, uri):
        """
        When a request for a URI comes in, we need to check
        if it is already in the cache, but the response hasn't
        yet been generated to determine the vary headers.
        We can assume the Vary headers do not change for a
        given URI, so use the Vary headers from a previous
        response (any will do).
        """
        vary_store = self.uri_store.get(uri)
        if not vary_store:
            # No values exist for this URI
            raise KeyError(uri)
        # Return the first value
        for s in vary_store.values():
            return s

    def __getitem__(self, key):
        return self.get(key)
        
    def get(self, key, *args, **kwargs):
        uri, h_vals = key
        vary_store = self.uri_store.get(uri, {})
        return vary_store.get(h_vals, *args, **kwargs)
        
    def __setitem__(self, key, value):
        uri, h_vals = key
        vary_store = self.uri_store.setdefault(uri, {})
        vary_store[h_vals] = value
    
    def __delitem__(self, key):
        uri, h_vals = key
        vary_store = self.uri_store[uri]
        del vary_store[h_vals]
        if not vary_store:
            # if the vary store is empty, delete the URI entry also
            del self.uri_store[uri]
    
    def pop(self, key, *args, **kwargs):
        item = self.get(key, *args, **kwargs)
        del self[key]
    
    def __len__(self):
        lengths = [len(store) for store in self.uri_store.values()]
        return sum(lengths)

class VaryHeaderUnawareStore(dict):
    def get_key_from_request(request, response=None):
        return cherrypy.url(qs=request.query_string)
    get_key_from_request = staticmethod(get_key_from_request)

class MemoryCache:
    
    maxobjects = 1000
    maxobj_size = 100000
    maxsize = 10000000
    delay = 600
    
    def __init__(self):
        self.clear()
        t = threading.Thread(target=self.expire_cache, name='expire_cache')
        self.expiration_thread = t
        if hasattr(threading.Thread, "daemon"):
            # Python 2.6+
            t.daemon = True
        else:
            t.setDaemon(True)
        t.start()
    
    def clear(self):
        """Reset the cache to its initial, empty state."""
        self.store = VaryHeaderAwareStore()
        self.expirations = {}
        self.tot_puts = 0
        self.tot_gets = 0
        self.tot_hist = 0
        self.tot_expires = 0
        self.tot_non_modified = 0
        self.cursize = 0
    
    def key(self):
        request = cherrypy.serving.request
        try:
            response = cherrypy.serving.response
        except AttributeError:
            response = None
        return self.store.get_key_from_request(request, response)
    
    def expire_cache(self):
        # expire_cache runs in a separate thread which the servers are
        # not aware of. It's possible that "time" will be set to None
        # arbitrarily, so we check "while time" to avoid exceptions.
        # See tickets #99 and #180 for more information.
        while time:
            now = time.time()
            # Must make a copy of expirations so it doesn't change size
            # during iteration
            for expiration_time, objects in self.expirations.items():
                if expiration_time <= now:
                    for obj_size, obj_key in objects:
                        try:
                            del self.store[obj_key]
                            self.tot_expires += 1
                            self.cursize -= obj_size
                        except KeyError:
                            # the key may have been deleted elsewhere
                            pass
                    del self.expirations[expiration_time]
            time.sleep(0.1)
    
    def get(self):
        """Return the object if in the cache, else None."""
        self.tot_gets += 1
        cache_item = self.store.get(self.key(), None)
        if cache_item:
            self.tot_hist += 1
            return cache_item
        else:
            return None
    
    def put(self, obj):
        if len(self.store) < self.maxobjects:
            # Size check no longer includes header length
            obj_size = len(obj[2])
            total_size = self.cursize + obj_size
            
            # checks if there's space for the object
            if (obj_size < self.maxobj_size and total_size < self.maxsize):
                # add to the expirations list and cache
                expiration_time = cherrypy.serving.response.time + self.delay
                obj_key = self.key()
                bucket = self.expirations.setdefault(expiration_time, [])
                bucket.append((obj_size, obj_key))
                self.store[obj_key] = obj
                self.tot_puts += 1
                self.cursize = total_size
    
    def delete(self):
        self.store.pop(self.key(), None)


def get(invalid_methods=("POST", "PUT", "DELETE"), debug=False, **kwargs):
    """Try to obtain cached output. If fresh enough, raise HTTPError(304).
    
    If POST, PUT, or DELETE:
        * invalidates (deletes) any cached response for this resource
        * sets request.cached = False
        * sets request.cacheable = False
    
    else if a cached copy exists:
        * sets request.cached = True
        * sets request.cacheable = False
        * sets response.headers to the cached values
        * checks the cached Last-Modified response header against the
            current If-(Un)Modified-Since request headers; raises 304
            if necessary.
        * sets response.status and response.body to the cached values
        * returns True
    
    otherwise:
        * sets request.cached = False
        * sets request.cacheable = True
        * returns False
    """
    request = cherrypy.serving.request
    response = cherrypy.serving.response
    
    # POST, PUT, DELETE should invalidate (delete) the cached copy.
    # See http://www.w3.org/Protocols/rfc2616/rfc2616-sec13.html#sec13.10.
    if request.method in invalid_methods:
        if debug:
            cherrypy.log('request.method %r in invalid_methods %r' %
                         (request.method, invalid_methods), 'TOOLS.CACHING')
        cherrypy._cache.delete()
        request.cached = False
        request.cacheable = False
        return False
    
    cache_data = cherrypy._cache.get()
    request.cached = c = bool(cache_data)
    request.cacheable = not c
    if c:
        if debug:
            cherrypy.log('Reading response from cache', 'TOOLS.CACHING')
        s, h, b, create_time, original_req_headers = cache_data
        
        # Copy the response headers. See http://www.cherrypy.org/ticket/721.
        response.headers = rh = httputil.HeaderMap()
        for k in h:
            dict.__setitem__(rh, k, dict.__getitem__(h, k))
        
        # Add the required Age header
        response.headers["Age"] = str(int(response.time - create_time))
        
        try:
            # Note that validate_since depends on a Last-Modified header;
            # this was put into the cached copy, and should have been
            # resurrected just above (response.headers = cache_data[1]).
            cptools.validate_since()
        except cherrypy.HTTPRedirect, x:
            if x.status == 304:
                cherrypy._cache.tot_non_modified += 1
            raise
        
        # serve it & get out from the request
        response.status = s
        response.body = b
    else:
        if debug:
            cherrypy.log('request is not cached', 'TOOLS.CACHING')
    return c


def tee_output():
    def tee(body):
        """Tee response.body into a list."""
        output = []
        for chunk in body:
            output.append(chunk)
            yield chunk
        
        # Might as well do this here; why cache if the body isn't consumed?
        if response.headers.get('Pragma', None) != 'no-cache':
            # save the cache data
            body = ''.join(output)
            vary = [he.value for he in response.headers.elements('Vary')]
            sel_headers = dict([(k, v) for k, v
                                in cherrypy.serving.request.headers.items()
                                if k in vary])
            cherrypy._cache.put((response.status, response.headers or {},
                                 body, response.time, sel_headers))
    
    response = cherrypy.serving.response
    response.body = tee(response.body)


def expires(secs=0, force=False, debug=False):
    """Tool for influencing cache mechanisms using the 'Expires' header.
    
    'secs' must be either an int or a datetime.timedelta, and indicates the
    number of seconds between response.time and when the response should
    expire. The 'Expires' header will be set to (response.time + secs).
    
    If 'secs' is zero, the 'Expires' header is set one year in the past, and
    the following "cache prevention" headers are also set:
       'Pragma': 'no-cache'
       'Cache-Control': 'no-cache, must-revalidate'
    
    If 'force' is False (the default), the following headers are checked:
    'Etag', 'Last-Modified', 'Age', 'Expires'. If any are already present,
    none of the above response headers are set.
    """
    
    response = cherrypy.serving.response
    headers = response.headers
    
    cacheable = False
    if not force:
        # some header names that indicate that the response can be cached
        for indicator in ('Etag', 'Last-Modified', 'Age', 'Expires'):
            if indicator in headers:
                cacheable = True
                break
    
    if not cacheable and not force:
        if debug:
            cherrypy.log('request is not cacheable', 'TOOLS.EXPIRES')
    else:
        if debug:
            cherrypy.log('request is cacheable', 'TOOLS.EXPIRES')
        if isinstance(secs, datetime.timedelta):
            secs = (86400 * secs.days) + secs.seconds
        
        if secs == 0:
            if force or ("Pragma" not in headers):
                headers["Pragma"] = "no-cache"
            if cherrypy.serving.request.protocol >= (1, 1):
                if force or "Cache-Control" not in headers:
                    headers["Cache-Control"] = "no-cache, must-revalidate"
            # Set an explicit Expires date in the past.
            expiry = httputil.HTTPDate(1169942400.0)
        else:
            expiry = httputil.HTTPDate(response.time + secs)
        if force or "Expires" not in headers:
            headers["Expires"] = expiry
