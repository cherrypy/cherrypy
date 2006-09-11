import datetime
import threading
import time

import cherrypy
from cherrypy.lib import cptools, http


class MemoryCache:
    
    def __init__(self):
        self.clear()
        t = threading.Thread(target=self.expire_cache, name='expire_cache')
        self.expiration_thread = t
        t.setDaemon(True)
        t.start()
    
    def clear(self):
        """Reset the cache to its initial, empty state."""
        self.cache = {}
        self.expirations = {}
        self.tot_puts = 0
        self.tot_gets = 0
        self.tot_hist = 0
        self.tot_expires = 0
        self.tot_non_modified = 0
        self.cursize = 0
    
    def _key(self):
        request = cherrypy.request
        return request.config.get("tools.caching.key", cherrypy.url(qs=request.query_string))
    key = property(_key)
    
    def expire_cache(self):
        # expire_cache runs in a separate thread which the servers are
        # not aware of. It's possible that "time" will be set to None
        # arbitrarily, so we check "while time" to avoid exceptions.
        # See tickets #99 and #180 for more information.
        while time:
            now = time.time()
            for expiration_time, objects in self.expirations.items():
                if expiration_time <= now:
                    for obj_size, obj_key in objects:
                        try:
                            del self.cache[obj_key]
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
        cache_item = self.cache.get(self.key, None)
        if cache_item:
            self.tot_hist += 1
            return cache_item
        else:
            return None
    
    def put(self, obj):
        conf = cherrypy.request.config.get
        
        if len(self.cache) < conf("tools.caching.maxobjects", 1000):
            # Size check no longer includes header length
            obj_size = len(obj[2])
            maxobj_size = conf("tools.caching.maxobj_size", 100000)
            
            total_size = self.cursize + obj_size
            maxsize = conf("tools.caching.maxsize", 10000000)
            
            # checks if there's space for the object
            if (obj_size < maxobj_size and total_size < maxsize):
                # add to the expirations list and cache
                expiration_time = time.time() + conf("tools.caching.delay", 600)
                obj_key = self.key
                bucket = self.expirations.setdefault(expiration_time, [])
                bucket.append((obj_size, obj_key))
                self.cache[obj_key] = obj
                self.tot_puts += 1
                self.cursize = total_size


def get(invalid_methods=("POST", "PUT", "DELETE"), cache_class=MemoryCache):
    """Try to obtain cached output. If fresh enough, raise HTTPError(304)."""
    if not hasattr(cherrypy, "_cache"):
        cherrypy._cache = cache_class()
    
    request = cherrypy.request
    
    # Ignore POST, PUT, DELETE.
    # See http://www.w3.org/Protocols/rfc2616/rfc2616-sec13.html#sec13.10.
    if request.method in invalid_methods:
        request.cached = c = False
    else:
        cache_data = cherrypy._cache.get()
        request.cached = c = bool(cache_data)
    
    if c:
        response = cherrypy.response
        s, response.headers, b, create_time = cache_data
        
        # Add the required Age header
        response.headers["Age"] = str(int(time.time() - create_time))
        
        try:
            cptools.validate_since()
        except cherrypy.HTTPError, x:
            if x.status == 304:
                cherrypy._cache.tot_non_modified += 1
            raise
        
        # serve it & get out from the request
        response.status = s
        response.body = b
    return c


def tee_output():
    if cherrypy.request.cached:
        return
    
    response = cherrypy.response
    output = []
    def tee(body):
        """Tee response.body into a list."""
        for chunk in body:
            output.append(chunk)
            yield chunk
        # Might as well do this here; why cache if the body isn't consumed?
        if response.headers.get('Pragma', None) != 'no-cache':
            # save the cache data
            body = ''.join([chunk for chunk in output])
            create_time = time.time()
            cherrypy._cache.put((response.status, response.headers or {},
                                 body, create_time))
    response.body = tee(response.body)


def expires(secs=0, force=False):
    """Tool for influencing cache mechanisms using the 'Expires' header.
    
    'secs' must be either an int or a datetime.timedelta, and indicates the
    number of seconds between response.time and when the response should
    expire. The 'Expires' header will be set to (response.time + secs).
    
    If 'secs' is zero, the following "cache prevention" headers are also set:
       'Pragma': 'no-cache'
       'Cache-Control': 'no-cache'
    
    If 'force' is False (the default), the following headers are checked:
    'Etag', 'Last-Modified', 'Age', 'Expires'. If any are already present,
    none of the above response headers are set.
    """
    
    response = cherrypy.response
    
    cacheable = False
    if not force:
        # some header names that indicate that the response can be cached
        for indicator in ('Etag', 'Last-Modified', 'Age', 'Expires'):
            if indicator in response.headers:
                cacheable = True
                break
    
    if not cacheable:
        if isinstance(secs, datetime.timedelta):
            secs = (86400 * secs.days) + secs.seconds
        
        if secs == 0:
            if force or "Pragma" not in response.headers:
                response.headers["Pragma"] = "no-cache"
            if cherrypy.request.protocol >= (1, 1):
                if force or "Cache-Control" not in response.headers:
                    response.headers["Cache-Control"] = "no-cache"
        
        expiry = http.HTTPDate(response.time + secs)
        if force or "Expires" not in response.headers:
            response.headers["Expires"] = expiry
