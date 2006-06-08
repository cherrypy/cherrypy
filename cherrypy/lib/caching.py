import Queue
import threading
import time

import cherrypy
from cherrypy.lib import cptools


class MemoryCache:
    
    def __init__(self):
        self.clear()
        self.expirationQueue = Queue.Queue()
        t = threading.Thread(target=self.expireCache, name='expireCache')
        self.expirationThread = t
        t.setDaemon(True)
        t.start()
    
    def clear(self):
        """Reset the cache to its initial, empty state."""
        self.cache = {}
        self.totPuts = 0
        self.totGets = 0
        self.totHits = 0
        self.totExpires = 0
        self.totNonModified = 0
        self.cursize = 0
    
    def _key(self):
        return cherrypy.request.config.get("tools.caching.key", cherrypy.request.browser_url)
    key = property(_key)
    
    def _maxobjsize(self):
        return cherrypy.request.config.get("tools.caching.maxobjsize", 100000)
    maxobjsize = property(_maxobjsize)
    
    def _maxsize(self):
        return cherrypy.request.config.get("tools.caching.maxsize", 10000000)
    maxsize = property(_maxsize)
    
    def _maxobjects(self):
        return cherrypy.request.config.get("tools.caching.maxobjects", 1000)
    maxobjects = property(_maxobjects)
    
    def expireCache(self):
        while True:
            expirationTime, objSize, objKey = self.expirationQueue.get(block=True, timeout=None)
            # expireCache runs in a separate thread which the servers are
            # not aware of. It's possible that "time" will be set to None
            # arbitrarily, so we check "while time" to avoid exceptions.
            # See tickets #99 and #180 for more information.
            while time and (time.time() < expirationTime):
                time.sleep(0.1)
            try:
                del self.cache[objKey]
                self.totExpires += 1
                self.cursize -= objSize
            except KeyError:
                # the key may have been deleted elsewhere
                pass
    
    def get(self):
        """
        If the content is in the cache, returns a tuple containing the 
        expiration time, the lastModified response header and the object 
        (rendered as a string); returns None if the key is not found.
        """
        self.totGets += 1
        cacheItem = self.cache.get(self.key, None)
        if cacheItem:
            self.totHits += 1
            return cacheItem
        else:
            return None
    
    def put(self, lastModified, obj):
        # Size check no longer includes header length
        objSize = len(obj[2])
        totalSize = self.cursize + objSize
        
        # checks if there's space for the object
        if ((objSize < self.maxobjsize) and 
            (totalSize < self.maxsize) and 
            (len(self.cache) < self.maxobjects)):
            # add to the expirationQueue & cache
            try:
                expirationTime = time.time() + cherrypy.request.config.get("tools.caching.delay", 600)
                objKey = self.key
                self.expirationQueue.put((expirationTime, objSize, objKey))
                self.cache[objKey] = (expirationTime, lastModified, obj)
                self.totPuts += 1
                self.cursize += objSize
            except Queue.Full:
                # can't add because the queue is full
                return


def init(cache_class=None):
    if cache_class is None:
        cache_class = MemoryCache
    cherrypy._cache = cache_class()

def get():
    # Ignore POST, PUT, DELETE.
    # See http://www.w3.org/Protocols/rfc2616/rfc2616-sec13.html#sec13.10.
    if cherrypy.request.method in cherrypy.config.get("tools.caching.invalid_methods",
                                                      ("POST", "PUT", "DELETE")):
        cherrypy.request.cached = c = False
    else:
        cacheData = cherrypy._cache.get()
        cherrypy.request.cached = c = bool(cacheData)
    
    if c:
        expirationTime, lastModified, obj = cacheData
        s, cherrypy.response.header_list, b = obj
        try:
            cptools.validate_since()
        except cherrypy.HTTPError, x:
            if x.status == 304:
                cherrypy._cache.totNonModified += 1
            raise
        
        # serve it & get out from the request
        cherrypy.response.status = s
        cherrypy.response.body = b
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
            lastModified = response.headers.get('Last-Modified', None)
            body = ''.join([chunk for chunk in output])
            cherrypy._cache.put(lastModified,
                                (response.status, response.header_list, body))
    response.body = tee(response.body)


# CherryPy interfaces. Pick one.

def wrap(f):
    """Caching decorator."""
    def wrapper(*a, **kw):
        # There's are no parameters to get(), so there's no need
        # to merge values from config.
        if not get():
            f(*a, **kw)
            tee_output()
    return wrapper

def setup():
    """Hook caching into cherrypy.request using the given conf."""
    conf = cherrypy.request.toolmap.get("caching", {})
    if not getattr(cherrypy, "_cache", None):
        init(conf.get("class", None))
    def wrapper():
        if get():
            cherrypy.request.handler = None
        else:
            # Note the devious technique here of adding hooks on the fly
            cherrypy.request.hooks.attach('before_finalize', tee_output)
    cherrypy.request.hooks.attach('before_main', wrapper)

