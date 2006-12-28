import datetime
import Queue
import threading
import time

import cherrypy
from cherrypy.lib import httptools
import basefilter


class MemoryCache:
    
    def __init__(self):
        self.clear()
        self.expirationQueue = Queue.Queue()
        t = self.expirationThread = threading.Thread(target=self.expireCache,
                                                     name='expireCache')
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
        return cherrypy.config.get("cache_filter.key", cherrypy.request.browser_url)
    key = property(_key)
    
    def _maxobjsize(self):
        return cherrypy.config.get("cache_filter.maxobjsize", 100000)
    maxobjsize = property(_maxobjsize)
    
    def _maxsize(self):
        return cherrypy.config.get("cache_filter.maxsize", 10000000)
    maxsize = property(_maxsize)
    
    def _maxobjects(self):
        return cherrypy.config.get("cache_filter.maxobjects", 1000)
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
                expirationTime = cherrypy.response.time + cherrypy.config.get("cache_filter.delay", 600)
                objKey = self.key
                self.expirationQueue.put((expirationTime, objSize, objKey))
                self.cache[objKey] = (expirationTime, lastModified, obj)
                self.totPuts += 1
                self.cursize += objSize
            except Queue.Full:
                # can't add because the queue is full
                return
    
    def delete(self):
        self.cache.pop(self.key)


class CacheFilter(basefilter.BaseFilter):
    """If the page is already stored in the cache, serves the contents.
    If the page is not in the cache, caches the output.
    """
    
    def __init__(self):
        cache_class = cherrypy.config.get("cache_filter.cacheClass", MemoryCache)
        cherrypy._cache = cache_class()
    
    def on_start_resource(self):
        cherrypy.request.cacheable = False
    
    def before_main(self):
        if not cherrypy.config.get('cache_filter.on', False):
            return
        
        request = cherrypy.request
        response = cherrypy.response
        
        # POST, PUT, DELETE should invalidate (delete) the cached copy.
        # See http://www.w3.org/Protocols/rfc2616/rfc2616-sec13.html#sec13.10.
        if request.method in cherrypy.config.get("cache_filter.invalid_methods",
                                                 ("POST", "PUT", "DELETE")):
            cherrypy._cache.delete()
            return
        
        cacheData = cherrypy._cache.get()
        if cacheData:
            # found a hit! check the if-modified-since request header
            expirationTime, lastModified, obj = cacheData
            s, h, b, create_time = obj
            modifiedSince = request.headers.get('If-Modified-Since', None)
            if modifiedSince is not None and modifiedSince == lastModified:
                cherrypy._cache.totNonModified += 1
                response.status = "304 Not Modified"
                ct = h.get('Content-Type', None)
                if ct:
                    response.headers['Content-Type'] = ct
                response.body = None
            else:
                # serve it & get out from the request
                response = cherrypy.response
                response.status, response.headers, response.body = s, h, b
            response.headers['Age'] = str(int(time.time() - create_time))
            request.execute_main = False
        else:
            request.cacheable = True
    
    def before_finalize(self):
        if not cherrypy.request.cacheable:
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
        if not cherrypy.request.cacheable:
            return
        
        response = cherrypy.response
        if response.headers.get('Pragma', None) != 'no-cache':
            lastModified = response.headers.get('Last-Modified', None)
            # save the cache data
            body = ''.join([chunk for chunk in response._cachefilter_tee])
            create_time = time.time()
            cherrypy._cache.put(lastModified, (response.status,
                                               response.headers,
                                               body,
                                               create_time))


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
            if force or ("Pragma" not in response.headers):
                response.headers["Pragma"] = "no-cache"
            if cherrypy.response.version >= "1.1":
                if force or ("Cache-Control" not in response.headers):
                    response.headers["Cache-Control"] = "no-cache"
        
        expiry = httptools.HTTPDate(time.gmtime(response.time + secs))
        if force or ("Expires" not in response.headers):
            response.headers["Expires"] = expiry
