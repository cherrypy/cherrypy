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

"""
Tools which both the CherryPy framework and application developers invoke.
"""

from BaseHTTPServer import BaseHTTPRequestHandler
responseCodes = BaseHTTPRequestHandler.responses

import inspect
import mimetools

import mimetypes
mimetypes.types_map['.dwg']='image/x-dwg'
mimetypes.types_map['.ico']='image/x-icon'

import os
import sys
import time


import cherrypy


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


class PositionalParametersAware(object):
    """
    Utility class that restores positional parameters functionality that
    was found in 2.0.0-beta.

    Use case:

    from cherrypy.lib import cptools
    import cherrypy
    class Root(cptools.PositionalParametersAware):
        def something(self, name):
            return "hello, " + name
        something.exposed
    cherrypy.root = Root()
    cherrypy.server.start()

    Now, fetch http://localhost:8080/something/name_is_here
    """
    def default( self, *args, **kwargs ):
        # remap parameters to fix positional parameters
        if len(args) == 0:
            args = ("index",)
        m = getattr(self, args[0], None)
        if m and getattr(m, "exposed", False):
            return getattr(self, args[0])(*args[1:], **kwargs)
        else:
            m = getattr(self, "index", None)
            if m and getattr(m, "exposed", False):
                try:
                    return self.index(*args, **kwargs)
                except TypeError:
                    pass
            raise cherrypy.NotFound()
    default.exposed = True


weekdayname = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
monthname = [None, 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

def HTTPDate(dt=None):
    """Return the given time.struct_time as a string in RFC 1123 format.
    
    If no arguments are provided, the current time (as determined by
    time.gmtime() is used).
    
    RFC 2616: "[Concerning RFC 1123, RFC 850, asctime date formats]...
    HTTP/1.1 clients and servers that parse the date value MUST
    accept all three formats (for compatibility with HTTP/1.0),
    though they MUST only generate the RFC 1123 format for
    representing HTTP-date values in header fields."
    
    RFC 1945 (HTTP/1.0) requires the same.
    
    """
    
    if dt is None:
        dt = time.gmtime()
    
    year, month, day, hh, mm, ss, wd, y, z = dt
    # Is "%a, %d %b %Y %H:%M:%S GMT" better or worse?
    return ("%s, %02d %3s %4d %02d:%02d:%02d GMT" %
            (weekdayname[wd], day, monthname[month], year, hh, mm, ss))


def getRanges(content_length):
    """Return a list of (start, stop) indices from a Range header, or None.
    
    Each (start, stop) tuple will be composed of two ints, which are suitable
    for use in a slicing operation. That is, the header "Range: bytes=3-6",
    if applied against a Python string, is requesting resource[3:7]. This
    function will return the list [(3, 7)].
    """
    
    r = cherrypy.request.headerMap.get('Range')
    if not r:
        return None
    
    result = []
    bytesunit, byteranges = r.split("=", 1)
    for brange in byteranges.split(","):
        start, stop = [x.strip() for x in brange.split("-", 1)]
        if start:
            if not stop:
                stop = content_length - 1
            start, stop = map(int, (start, stop))
            if start >= content_length:
                # From rfc 2616 sec 14.16:
                # "If the server receives a request (other than one
                # including an If-Range request-header field) with an
                # unsatisfiable Range request-header field (that is,
                # all of whose byte-range-spec values have a first-byte-pos
                # value greater than the current length of the selected
                # resource), it SHOULD return a response code of 416
                # (Requested range not satisfiable)."
                continue
            if stop < start:
                # From rfc 2616 sec 14.16:
                # "If the server ignores a byte-range-spec because it
                # is syntactically invalid, the server SHOULD treat
                # the request as if the invalid Range header field
                # did not exist. (Normally, this means return a 200
                # response containing the full entity)."
                return None
            result.append((start, stop + 1))
        else:
            if not stop:
                # See rfc quote above.
                return None
            # Negative subscript (last N bytes)
            result.append((content_length - int(stop), content_length))
    
    if result == []:
        cherrypy.response.headerMap['Content-Range'] = "bytes */%s" % content_length
        message = "Invalid Range (first-byte-pos greater than Content-Length)"
        raise cherrypy.HTTPError(416, message)
    
    return result


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
        if getattr(cherrypy, "debug", None):
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
    
    strModifTime = HTTPDate(time.gmtime(stat.st_mtime))
    if cherrypy.request.headerMap.has_key('If-Modified-Since'):
        # Check if if-modified-since date is the same as strModifTime
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
        r = getRanges(c_len)
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

def validStatus(status):
    """Return legal HTTP status Code, Reason-phrase and Message.
    
    The status arg must be an int, or a str that begins with an int.
    
    If status is an int, or a str and  no reason-phrase is supplied,
    a default reason-phrase will be provided.
    """
    
    if not status:
        status = 200
    
    status = str(status)
    parts = status.split(" ", 1)
    if len(parts) == 1:
        # No reason supplied.
        code, = parts
        reason = None
    else:
        code, reason = parts
        reason = reason.strip()
    
    try:
        code = int(code)
    except ValueError:
        raise cherrypy.HTTPError(500, "Illegal response status from server (non-numeric).")
    
    if code < 100 or code > 599:
        raise cherrypy.HTTPError(500, "Illegal response status from server (out of range).")
    
    if code not in responseCodes:
        # code is unknown but not illegal
        defaultReason, message = "", ""
    else:
        defaultReason, message = responseCodes[code]
    
    if reason is None:
        reason = defaultReason
    
    return code, reason, message
