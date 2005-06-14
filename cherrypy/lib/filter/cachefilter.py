"""
Copyright (c) 2004, CherryPy Team (team@cherrypy.org)
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, 
are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice, 
      this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice, 
      this list of conditions and the following disclaimer in the documentation 
      and/or other materials provided with the distribution.
    * Neither the name of the CherryPy Team nor the names of its contributors 
      may be used to endorse or promote products derived from this software 
      without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND 
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED 
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE 
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE 
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL 
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR 
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER 
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, 
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE 
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import threading
import Queue
import time

import basefilter

def defaultCacheKey():
    return cpg.request.browserUrl


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
    
    def __init__(
            self, 
            CacheClass=MemoryCache,
            key=defaultCacheKey, 
            delay=600,         # 10 minutes
            maxobjsize=100000, # 100 KB
            maxsize=10000000,  # 10 MB
            maxobjects=1000    # 1000 objects
            ):
        self.CacheClass = CacheClass
        self.key = key
        self.delay = delay
        self.maxobjsize = maxobjsize
        self.maxsize = maxsize
        self.maxobjects = maxobjects
    
    def onStartResource(self):
        # We have to dynamically import cpg because Python can't handle
        #   circular module imports :-(
        global cpg, cperror
        from cherrypy import cpg, cperror
        cpg.threadData.cacheable = True
    
    def beforeMain(self):
        if not cpg.config.get('cacheFilter.on', False):
            return
        
        if not hasattr(cpg, '_cache'):
            cpg._cache = self.CacheClass(self.key, self.delay,
                self.maxobjsize, self.maxsize, self.maxobjects)
        
        cacheData = cpg._cache.get()
        cpg.threadData.cacheable = not cacheData
        if cacheData:
            expirationTime, lastModified, obj = cacheData
            # found a hit! check the if-modified-since request header
            modifiedSince = cpg.request.headerMap.get('If-Modified-Since', None)
            # print ("Cache hit: If-Modified-Since=%s, lastModified=%s" %
            #        (modifiedSince, lastModified))
            if modifiedSince is not None and modifiedSince == lastModified:
                cpg._cache.totNonModified += 1
                cpg.response.status = "304 Not Modified"
                cpg.response.body = []
            else:
                # serve it & get out from the request
                cpg.response.status, cpg.response.headers, body = obj
                cpg.response.body = body
            raise cperror.RequestHandled
    
    def onEndResource(self):
        """Close & fix the cache entry after content was fully written"""
        if not cpg.config.get('cacheFilter.on', False):
            return
        
        if cpg.threadData.cacheable:
            status = cpg.response.status
            headers = cpg.response.headers
            
            # Consume the body iterable. Only do this once!
            body = cpg.response.body = [chunk for chunk in cpg.response.body]
            
            if cpg.response.headerMap.get('Pragma', None) != 'no-cache':
                lastModified = cpg.response.headerMap.get('Last-Modified', None)
                # saves the cache data
                cpg._cache.put(lastModified, (status, headers, body))


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
        cpg.response.headerMap['Content-Type'] = 'text/plain'
        cpg.response.headerMap['Pragma'] = 'no-cache'
        cache = cpg._cache
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
