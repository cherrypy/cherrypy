:tocdepth: 1

*******
Caching
*******

CherryPy implements a simple caching system as a pluggable Tool. This tool tries
to be an (in-process) HTTP/1.1-compliant cache. It's not quite there yet, but
it's probably good enough for most sites.

In general, GET responses are cached (along with selecting headers) and, if
another request arrives for the same resource, the caching Tool will return 304
Not Modified if possible, or serve the cached response otherwise. It also sets
request.cached to True if serving a cached representation, and sets request.cacheable
to False (so it doesn't get cached again).

If POST, PUT, or DELETE requests are made for a cached resource, they invalidate
(delete) any cached response.

Usage
=====

::

    [/]
    tools.caching.on = True

Other configuration options:

* **tools.caching.cache_class**: a class that implements the basic ``get`` and
  ``put`` methods. The standard {{{MemoryCache}}} stores the data in memory,
  using a standard Python dict. Provide this entry to implement custom caching
  repositories; for example on disk, or in a database.
* **tools.caching.key**: this defaults to the browser URL (including the querystring).
* **tools.caching.delay**: time in seconds until the cached content expires;
  defaults to 600 (10 minutes).
* **tools.caching.maxobjsize**: max size of each cached object in bytes;
  defaults to 100000 bytes (100 KB).
* **tools.caching.maxsize**: max size of the entire cache in bytes;
  defaults to 10000000 (10 MB).
* **tools.caching.maxobjects**: max number of cached objects; defaults to 1000.

