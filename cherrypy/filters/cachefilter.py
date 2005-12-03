
import threading
import Queue
import time

import cherrypy
import basefilter

def defaultCacheKey():
    return cherrypy.request.browserUrl


class MemoryCache:

    def __init__(self, key, delay, maxobjsize, maxsize, maxobjects):
        self.key = key
        self.delay = delay
        self.maxobjsize = maxobjsize
        self.maxsize = maxsize
        self.maxobjects = maxobjects
        self.cursize = 0
        self.cache = {}
        self.expirationQueue = Queue.Queue()
        self.expirationThread = threading.Thread(target=self.expireCache, name='expireCache')
        self.expirationThread.setDaemon(True)
        self.expirationThread.start()
        self.totPuts = 0
        self.totGets = 0
        self.totHits = 0
        self.totExpires = 0
        self.totNonModified = 0

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
        cacheItem = self.cache.get(self.key(), None)
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
                expirationTime = time.time() + self.delay
                objKey = self.key()
                self.expirationQueue.put((expirationTime, objSize, objKey))
                self.totPuts += 1
                self.cursize += objSize
            except Queue.Full:
                # can't add because the queue is full
                return
            self.cache[objKey] = (expirationTime, lastModified, obj)


class CacheFilter(basefilter.BaseFilter):
    """If the page is already stored in the cache, serves the contents.
    If the page is not in the cache, caches the output.
    """
    
    CacheClass = property(lambda self: cherrypy.config.get("cache_filter.cacheClass", MemoryCache))
    key = property(lambda self: cherrypy.config.get("cache_filter.key", defaultCacheKey))
    delay = property(lambda self: cherrypy.config.get("cache_filter.delay", 600))
    maxobjsize = property(lambda self: cherrypy.config.get("cache_filter.maxobjsize", 100000))
    maxsize = property(lambda self: cherrypy.config.get("cache_filter.maxsize", 10000000))
    maxobjects = property(lambda self: cherrypy.config.get("cache_filter.maxobjects", 1000))
    
    def before_main(self):
        if not cherrypy.config.get('cache_filter.on', False):
            return
        
        if not hasattr(cherrypy, '_cache'):
            cherrypy._cache = self.CacheClass(self.key, self.delay,
                self.maxobjsize, self.maxsize, self.maxobjects)
        
        cacheData = cherrypy._cache.get()
        cherrypy.request.cacheable = not cacheData
        if cacheData:
            # found a hit! check the if-modified-since request header
            expirationTime, lastModified, obj = cacheData
            modifiedSince = cherrypy.request.headers.get('If-Modified-Since', None)
            if modifiedSince is not None and modifiedSince == lastModified:
                cherrypy._cache.totNonModified += 1
                cherrypy.response.status = "304 Not Modified"
                cherrypy.response.body = None
            else:
                # serve it & get out from the request
                cherrypy.response.status, cherrypy.response.headers, body = obj
                cherrypy.response.body = body
            raise cherrypy.RequestHandled()
    
    def before_finalize(self):
        if not (cherrypy.config.get('cache_filter.on', False) and
                cherrypy.request.cacheable):
            return
        
        cherrypy.response._cachefilter_tee = []
        def tee(body):
            """Tee response.body into response._cachefilter_tee (a list)."""
            for chunk in body:
                cherrypy.response._cachefilter_tee.append(chunk)
                yield chunk
        cherrypy.response.body = tee(cherrypy.response.body)
    
    def on_end_request(self):
        # Close & fix the cache entry after content was fully written
        if not (cherrypy.config.get('cache_filter.on', False) and
                cherrypy.request.cacheable):
            return
        
        response = cherrypy.response
        status = response.status
        headers = response.headers
        body = ''.join([chunk for chunk in response._cachefilter_tee])
        
        if response.headers.get('Pragma', None) != 'no-cache':
            lastModified = response.headers.get('Last-Modified', None)
            # saves the cache data
            cherrypy._cache.put(lastModified, (status, headers, body))


def percentual(n,d):
    """calculates the percentual, dealing with div by zeros"""
    if d == 0:
        return 0
    else:
        return (float(n)/float(d))*100

def formatSize(n):
    """formats a number as a memory size, in bytes, kbytes, MB, GB)"""
    if n < 1024:
        return "%4d bytes" % n
    elif n < 1024*1024:
        return "%4d kbytes" % (n / 1024)
    elif n < 1024*1024*1024:
        return "%4d MB" % (n / (1024*1024))
    else:
        return "%4d GB" % (n / (1024*1024*1024))


class CacheStats:
    
    def index(self):
        cherrypy.response.headers['Content-Type'] = 'text/plain'
        cherrypy.response.headers['Pragma'] = 'no-cache'
        cache = cherrypy._cache
        yield "Cache statistics\n"
        yield "Maximum object size: %s\n" % formatSize(cache.maxobjsize)
        yield "Maximum cache size: %s\n" % formatSize(cache.maxsize)
        yield "Maximum number of objects: %d\n" % cache.maxobjects
        yield "Current cache size: %s\n" % formatSize(cache.cursize)
        yield "Approximated expiration queue size: %d\n" % cache.expirationQueue.qsize()
        yield "Number of cache entries: %d\n" % len(cache.cache)
        yield "Total cache writes: %d\n" % cache.totPuts
        yield "Total cache read attempts: %d\n" % cache.totGets
        yield "Total hits: %d (%1.2f%%)\n" % (cache.totHits, percentual(cache.totHits, cache.totGets))
        yield "Total misses: %d (%1.2f%%)\n" % (cache.totGets-cache.totHits, percentual(cache.totGets-cache.totHits, cache.totGets))
        yield "Total expires: %d\n" % cache.totExpires
        yield "Total non-modified content: %d\n" % cache.totNonModified
    index.exposed = True
