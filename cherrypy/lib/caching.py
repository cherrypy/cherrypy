import datetime
import threading
import time

import cherrypy
from cherrypy.lib import cptools, http


class MemoryCache:
    
    def __init__(self):
        self.clear()
        t = threading.Thread(target=self.expireCache, name='expireCache')
        self.expirationThread = t
        t.setDaemon(True)
        t.start()
    
    def clear(self):
        """Reset the cache to its initial, empty state."""
        self.cache = {}
        self.expirations = {}
        self.totPuts = 0
        self.totGets = 0
        self.totHits = 0
        self.totExpires = 0
        self.totNonModified = 0
        self.cursize = 0
    
    def _key(self):
        return cherrypy.request.config.get("tools.caching.key", cherrypy.request.browser_url)
    key = property(_key)
    
    def expireCache(self):
        # expireCache runs in a separate thread which the servers are
        # not aware of. It's possible that "time" will be set to None
        # arbitrarily, so we check "while time" to avoid exceptions.
        # See tickets #99 and #180 for more information.
        while time:
            now = time.time()
            for expirationTime, objects in self.expirations.items():
                if expirationTime <= now:
                    for objSize, objKey in objects:
                        try:
                            del self.cache[objKey]
                            self.totExpires += 1
                            self.cursize -= objSize
                        except KeyError:
                            # the key may have been deleted elsewhere
                            pass
                    del self.expirations[expirationTime]
            time.sleep(0.1)
    
    def get(self):
        """Return the object if in the cache, else None."""
        self.totGets += 1
        cacheItem = self.cache.get(self.key, None)
        if cacheItem:
            self.totHits += 1
            return cacheItem
        else:
            return None
    
    def put(self, obj):
        conf = cherrypy.request.config.get
        
        if len(self.cache) < conf("tools.caching.maxobjects", 1000):
            # Size check no longer includes header length
            objSize = len(obj[2])
            maxobjsize = conf("tools.caching.maxobjsize", 100000)
            
            totalSize = self.cursize + objSize
            maxsize = conf("tools.caching.maxsize", 10000000)
            
            # checks if there's space for the object
            if (objSize < maxobjsize and totalSize < maxsize):
                # add to the expirations list and cache
                expirationTime = time.time() + conf("tools.caching.delay", 600)
                objKey = self.key
                bucket = self.expirations.setdefault(expirationTime, [])
                bucket.append((objSize, objKey))
                self.cache[objKey] = obj
                self.totPuts += 1
                self.cursize = totalSize


def init(cache_class=None):
    if cache_class is None:
        cache_class = MemoryCache
    cherrypy._cache = cache_class()

def get():
    # Ignore POST, PUT, DELETE.
    # See http://www.w3.org/Protocols/rfc2616/rfc2616-sec13.html#sec13.10.
    invalid = cherrypy.config.get("tools.caching.invalid_methods",
                                  ("POST", "PUT", "DELETE"))
    if cherrypy.request.method in invalid:
        cherrypy.request.cached = c = False
    else:
        cacheData = cherrypy._cache.get()
        cherrypy.request.cached = c = bool(cacheData)
    
    if c:
        response = cherrypy.response
        s, response.headers, b, create_time = cacheData
        
        # Add the required Age header
        response.headers["Age"] = str(int(time.time() - create_time))
        
        try:
            cptools.validate_since()
        except cherrypy.HTTPError, x:
            if x.status == 304:
                cherrypy._cache.totNonModified += 1
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


# CherryPy interfaces. Pick one.

def enable(**kwargs):
    """Compile-time decorator (turn on the tool in config)."""
    def wrapper(f):
        if not hasattr(f, "_cp_config"):
            f._cp_config = {}
        f._cp_config["tools.caching.on"] = True
        for k, v in kwargs.iteritems():
            f._cp_config["tools.caching." + k] = v
        return f
    return wrapper

def _wrapper():
    if get():
        cherrypy.request.handler = None
    else:
        # Note the devious technique here of adding hooks on the fly
        cherrypy.request.hooks.attach('before_finalize', tee_output)

def _setup():
    """Hook caching into cherrypy.request using the given conf."""
    conf = cherrypy.request.toolmap.get("caching", {})
    if not getattr(cherrypy, "_cache", None):
        init(conf.get("class", None))
    cherrypy.request.hooks.attach('before_main', _wrapper)

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
    none of the "cache prevention" headers are set.
    """
    
    if isinstance(secs, datetime.timedelta):
        secs = (86400 * secs.days) + secs.seconds
    expiry = http.HTTPDate(cherrypy.response.time + secs)
    cptools.response_headers([("Expires", expiry)], force)
    
    if secs == 0:
        cacheable = False
        if not force:
            # some header names that indicate that the response can be cached
            for indicator in ('Etag', 'Last-Modified', 'Age', 'Expires'):
                if indicator in cherrypy.response.headers:
                    cacheable = True
                    break
        if not cacheable:
            cptools.response_headers([("Pragma", "no-cache")], force)
            if cherrypy.request.version >= (1, 1):
                cptools.response_headers([("Cache-Control", "no-cache")], force)
