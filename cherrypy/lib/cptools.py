"""Tools which both CherryPy and application developers may invoke."""

import inspect
import mimetools
import mimetypes
mimetypes.types_map['.dwg']='image/x-dwg'
mimetypes.types_map['.ico']='image/x-icon'

import os
import sys
import time

import cherrypy
import httptools


def decorate(func, decorator):
    """
    Return the decorated func. This will automatically copy all
    non-standard attributes (like exposed) to the newly decorated function.
    """
    newfunc = decorator(func)
    for (k,v) in inspect.getmembers(func):
        if not hasattr(newfunc, k):
            setattr(newfunc, k, v)
    return newfunc

def decorateAll(obj, decorator):
    """
    Recursively decorate all exposed functions of obj and all of its children,
    grandchildren, etc. If you used to use aspects, you might want to look
    into these. This function modifies obj; there is no return value.
    """
    obj_type = type(obj)
    for (k,v) in inspect.getmembers(obj):
        if hasattr(obj_type, k): # only deal with user-defined attributes
            continue
        if callable(v) and getattr(v, "exposed", False):
            setattr(obj, k, decorate(v, decorator))
        decorateAll(v, decorator)


class ExposeItems:
    """
    Utility class that exposes a getitem-aware object. It does not provide
    index() or default() methods, and it does not expose the individual item
    objects - just the list or dict that contains them. User-specific index()
    and default() methods can be implemented by inheriting from this class.
    
    Use case:
    
    from cherrypy.lib.cptools import ExposeItems
    ...
    cherrypy.root.foo = ExposeItems(mylist)
    cherrypy.root.bar = ExposeItems(mydict)
    """
    exposed = True
    def __init__(self, items):
        self.items = items
    def __getattr__(self, key):
        return self.items[key]


def serveFile(path, contentType=None, disposition=None, name=None):
    """Set status, headers, and body in order to serve the given file.
    
    The Content-Type header will be set to the contentType arg, if provided.
    If not provided, the Content-Type will be guessed by its extension.
    
    If disposition is not None, the Content-Disposition header will be set
    to "<disposition>; filename=<name>". If name is None, it will be set
    to the basename of path. If disposition is None, no Content-Disposition
    header will be written.
    """
    
    response = cherrypy.response
    
    # If path is relative, make absolute using cherrypy.root's module.
    # If there is no cherrypy.root, or it doesn't have a __module__
    # attribute, then users should fix the issue by making path absolute.
    # That is, CherryPy should not guess where the application root is
    # any further than trying cherrypy.root.__module__, and it certainly
    # should *not* use cwd (since CP may be invoked from a variety of
    # paths). If using staticFilter, you can make your relative paths
    # become absolute by supplying a value for "staticFilter.root".
    if not os.path.isabs(path):
        root = os.path.dirname(sys.modules[cherrypy.root.__module__].__file__)
        path = os.path.join(root, path)
    
    try:
        stat = os.stat(path)
    except OSError:
        if cherrypy.config.get('server.logFileNotFound', False):
            cherrypy.log("    NOT FOUND file: %s" % path, "DEBUG")
        raise cherrypy.NotFound()
    
    if contentType is None:
        # Set content-type based on filename extension
        ext = ""
        i = path.rfind('.')
        if i != -1:
            ext = path[i:]
        contentType = mimetypes.types_map.get(ext, "text/plain")
    response.headerMap['Content-Type'] = contentType
    
    strModifTime = httptools.HTTPDate(time.gmtime(stat.st_mtime))
    if cherrypy.request.headerMap.has_key('If-Modified-Since'):
        if cherrypy.request.headerMap['If-Modified-Since'] == strModifTime:
            response.status = "304 Not Modified"
            response.body = []
            if getattr(cherrypy, "debug", None):
                cherrypy.log("    Found file (304 Not Modified): %s" % path, "DEBUG")
            return []
    response.headerMap['Last-Modified'] = strModifTime
    
    if disposition is not None:
        if name is None:
            name = os.path.basename(path)
        cd = "%s; filename=%s" % (disposition, name)
        response.headerMap["Content-Disposition"] = cd
    
    # Set Content-Length and use an iterable (file object)
    #   this way CP won't load the whole file in memory
    c_len = stat.st_size
    bodyfile = open(path, 'rb')
    if getattr(cherrypy, "debug", None):
        cherrypy.log("    Found file: %s" % path, "DEBUG")
    
    # HTTP/1.0 didn't have Range/Accept-Ranges headers, or the 206 code
    if cherrypy.response.version >= "1.1":
        response.headerMap["Accept-Ranges"] = "bytes"
        r = httptools.getRanges(cherrypy.request.headerMap.get('Range'), c_len)
        if r == []:
            response.headerMap['Content-Range'] = "bytes */%s" % c_len
            message = "Invalid Range (first-byte-pos greater than Content-Length)"
            raise cherrypy.HTTPError(416, message)
        if r:
            if len(r) == 1:
                # Return a single-part response.
                start, stop = r[0]
                r_len = stop - start
                response.status = "206 Partial Content"
                response.headerMap['Content-Range'] = ("bytes %s-%s/%s" %
                                                       (start, stop - 1, c_len))
                response.headerMap['Content-Length'] = r_len
                bodyfile.seek(start)
                response.body = [bodyfile.read(r_len)]
            else:
                # Return a multipart/byteranges response.
                response.status = "206 Partial Content"
                boundary = mimetools.choose_boundary()
                ct = "multipart/byteranges; boundary=%s" % boundary
                response.headerMap['Content-Type'] = ct
##                del response.headerMap['Content-Length']
                
                def fileRanges():
                    for start, stop in r:
                        yield "--" + boundary
                        yield "\nContent-type: %s" % contentType
                        yield ("\nContent-range: bytes %s-%s/%s\n\n"
                               % (start, stop - 1, c_len))
                        bodyfile.seek(start)
                        yield bodyfile.read((stop + 1) - start)
                        yield "\n"
                    # Final boundary
                    yield "--" + boundary
                response.body = fileRanges()
        else:
            response.headerMap['Content-Length'] = c_len
            response.body = fileGenerator(bodyfile)
    else:
        response.headerMap['Content-Length'] = c_len
        response.body = fileGenerator(bodyfile)
    return response.body

def fileGenerator(input, chunkSize=65536):
    """Yield the given input (a file object) in chunks (default 64k)."""
    chunk = input.read(chunkSize)
    while chunk:
        yield chunk
        chunk = input.read(chunkSize)
    input.close()
