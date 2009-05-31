from email.parser import FeedParser
import io
import re
import tempfile

import cherrypy
from cherrypy._cperror import MaxSizeExceeded
from cherrypy.lib import httputil


# -------------------------------- Processors -------------------------------- #

def unquote_plus(bs):
    """Bytes version of urllib.parse.unquote_plus."""
    bs = bs.replace(b'+', b' ')
    atoms = bs.split(b'%')
    for i in range(1, len(atoms)):
        item = atoms[i]
        try:
            pct = int(item[:2], 16)
            atoms[i] = bytes([pct]) + item[2:]
        except ValueError:
            pass
    return b''.join(atoms)

def process_urlencoded(entity):
    """Read application/x-www-form-urlencoded data into entity.params."""
    if not entity.headers.get("Content-Length", ""):
        # No Content-Length header supplied (or it's 0).
        # If we went ahead and called rfile.read(), it would hang,
        # since it cannot determine when to stop reading from the socket.
        # See http://www.cherrypy.org/ticket/493.
        # See also http://www.cherrypy.org/ticket/650.
        # Note also that we expect any HTTP server to have decoded
        # any message-body that had a transfer-coding, and we expect
        # the HTTP server to have supplied a Content-Length header
        # which is valid for the decoded entity-body.
        raise cherrypy.HTTPError(411)
    
    params = entity.params
    qs = entity.fp.read()
    for aparam in qs.split(b'&'):
        for pair in aparam.split(b';'):
            if not pair:
                continue
            
            atoms = pair.split(b'=', 1)
            if len(atoms) == 1:
                atoms.append(b'')
            
            key = unquote_plus(atoms[0]).decode(entity.encoding)
            value = unquote_plus(atoms[1]).decode(entity.encoding)
            
            if key in params:
                if not isinstance(params[key], list):
                    params[key] = [params[key]]
                params[key].append(value)
            else:
                params[key] = value

def process_multipart(entity):
    """Read all multipart parts into entity.parts."""
    ib = ""
    if 'boundary' in entity.content_type.params:
        # http://tools.ietf.org/html/rfc2046#section-5.1.1
        # "The grammar for parameters on the Content-type field is such that it
        # is often necessary to enclose the boundary parameter values in quotes
        # on the Content-type line"
        ib = entity.content_type.params['boundary'].strip('"')
    
    if not re.match("^[ -~]{0,200}[!-~]$", ib):
        raise ValueError('Invalid boundary in multipart form: %r' % (ib,))
    
    ib = bytes('--' + ib, 'ascii')
    
    # Find the first marker
    while True:
        b = entity.readline()
        if not b:
            return
        
        b = b.strip()
        if b == ib:
            break
    
    # Read all parts
    while True:
        part = Part.from_fp(entity.fp, ib)
        entity.parts.append(part)
        part.process()
        if part.fp.done:
            break

def process_multipart_form_data(entity):
    """Read all multipart/form-data parts into entity.parts or entity.params."""
    process_multipart(entity)
    
    kept_parts = []
    for part in entity.parts:
        if part.name is None:
            kept_parts.append(part)
        else:
            if part.filename is None:
                # It's a regular field
                entity.params[part.name] = part.fullvalue()
            else:
                # It's a file upload. Retain the whole part so consumer code
                # has access to its .file and .filename attributes.
                entity.params[part.name] = part
    
    entity.parts = kept_parts

def _old_process_multipart(entity):
    """The behavior of 3.2 and lower. Deprecated and will be changed in 3.3."""
    process_multipart(entity)
    
    params = entity.params
    
    for part in entity.parts:
        key = 'parts' if part.name is None else part.name
        
        if part.filename is None:
            # It's a regular field
            value = part.fullvalue()
        else:
            # It's a file upload. Retain the whole part so consumer code
            # has access to its .file and .filename attributes.
            value = part
        
        if key in params:
            if not isinstance(params[key], list):
                params[key] = [params[key]]
            params[key].append(value)
        else:
            params[key] = value



# --------------------------------- Entities --------------------------------- #


class Entity(object, metaclass=cherrypy._AttributeDocstrings):
    """An HTTP request body, or MIME multipart body."""
    
    params = None
    params__doc = """
    If the request Content-Type is 'application/x-www-form-urlencoded' or
    multipart, this will be a dict of the params pulled from the entity
    body; that is, it will be the portion of request.params that come
    from the message body (sometimes called "POST params", although they
    can be sent with various HTTP method verbs). This value is set between
    the 'before_request_body' and 'before_handler' hooks (assuming that
    process_request_body is True)."""

    default_content_type = 'application/x-www-form-urlencoded'
    # http://tools.ietf.org/html/rfc2046#section-4.1.2:
    # "The default character set, which must be assumed in the
    # absence of a charset parameter, is US-ASCII."
    default_text_encoding = 'us-ascii'
    # For MIME multiparts, if the payload has no charset, leave as bytes.
    default_encoding = None
    force_encoding = None
    processors = {'application/x-www-form-urlencoded': process_urlencoded,
                  'multipart/form-data': process_multipart_form_data,
                  'multipart': process_multipart,
                  }
    
    def __init__(self, fp, headers, params=None, parts=None):
        # Make an instance-specific copy of the class processors
        # so Tools, etc. can replace them per-request.
        # TODO: that makes it easy for request.body but not Parts. Fix.
        self.processors = self.processors.copy()
        
        self.fp = fp
        self.headers = headers
        
        if params is None:
            params = {}
        self.params = params
        
        if parts is None:
            parts = []
        self.parts = parts
        
        # Content-Type
        self.content_type = headers.elements('Content-Type')
        if self.content_type:
            self.content_type = self.content_type[0]
        else:
            self.content_type = httputil.HeaderElement.from_str(
                self.default_content_type)
        
        # Encoding
        self.encoding = self.best_encoding()
        
        # Length
        self.length = None
        clen = headers.get('Content-Length', None)
        if clen is not None:
            try:
                self.length = int(clen)
            except ValueError:
                pass
        
        # Content-Disposition
        self.name = None
        self.filename = None
        disp = headers.elements('Content-Disposition')
        if disp:
            disp = disp[0]
            if 'name' in disp.params:
                self.name = disp.params['name']
                if self.name.startswith('"') and self.name.endswith('"'):
                    self.name = self.name[1:-1]
            if 'filename' in disp.params:
                self.filename = disp.params['filename']
                if self.filename.startswith('"') and self.filename.endswith('"'):
                    self.filename = self.filename[1:-1]
    
    def best_encoding(self):
        """Return the best encoding based on Content-Type (and defaults)."""
        if self.force_encoding:
            return self.force_encoding
        
        encoding = self.content_type.params.get("charset", None)
        if not encoding:
            ct = self.content_type.value.lower()
            if ct.lower().startswith("text/"):
                return self.default_text_encoding
        
        return encoding or self.default_encoding
    
    def read(self, size=None, fp=None):
        return self.fp.read(size, fp)
    
    def readline(self, size=None):
        return self.fp.readline(size)
    
    def readlines(self, sizehint=None):
        return self.fp.readlines(sizehint)
    
    def __iter__(self):
        return self
    
    def __next__(self):
        line = self.readline()
        if not line:
            raise StopIteration
        return line
    
    def read_into_file(self, fp=None):
        """Read the request body into fp (or make_file() if None). Return fp."""
        if fp is None:
            fp = self.make_file()
        self.read(fp=fp)
        return fp
    
    def make_file(self):
        """Return a file into which the request body will be read.
        
        By default, this will return a TemporaryFile. Override as needed."""
        return tempfile.TemporaryFile()
    
    def fullvalue(self):
        """Return this entity as a string, whether stored in a file or not."""
        if self.file:
            # It was stored in a tempfile. Read it.
            self.file.seek(0)
            value = self.file.read()
            self.file.seek(0)
        else:
            value = self.value
        return value
    
    def process(self):
        """Execute the best-match processor for the given media type."""
        proc = None
        ct = self.content_type.value
        try:
            proc = self.processors[ct]
        except KeyError:
            toptype = ct.split('/', 1)[0]
            try:
                proc = self.processors[toptype]
            except KeyError:
                pass
        if proc is None:
            self.default_proc()
        else:
            proc(self)

    
    def default_proc(self):
        # Leave the fp alone for someone else to read. This works fine
        # for request.body, but the Part subclasses need to override this
        # so they can move on to the next part.
        pass


class Part(Entity):
    """A MIME part entity, part of a multipart entity."""
    
    default_content_type = 'text/plain; charset=us-ascii'
    # "The default character set, which must be assumed in the absence of a
    # charset parameter, is US-ASCII."
    default_encoding = 'us-ascii'
    # This is the default in stdlib cgi. We may want to increase it.
    maxrambytes = 1000
    
    def __init__(self, fp, headers, boundary):
        Entity.__init__(self, fp, headers)
        self.boundary = boundary
        self.file = None
        self.value = None
    
    def from_fp(cls, fp, boundary):
        headers = cls.read_headers(fp)
        return cls(fp, headers, boundary)
    from_fp = classmethod(from_fp)
    
    def read_headers(cls, fp):
        headers = httputil.HeaderMap()
        while True:
            line = fp.readline()
            if not line:
                # No more data--illegal end of headers
                raise EOFError("Illegal end of headers.")
            
            if line == b'\r\n':
                # Normal end of headers
                break
            if not line.endswith(b'\r\n'):
                raise ValueError("MIME requires CRLF terminators: %r" % line)
            
            if line[0] in b' \t':
                # It's a continuation line.
                v = line.strip().decode('ISO-8859-1')
            else:
                k, v = line.split(b":", 1)
                k = k.strip().decode('ISO-8859-1')
                v = v.strip().decode('ISO-8859-1')
            
            existing = headers.get(k)
            if existing:
                v = ", ".join((existing, v))
            headers[k] = v
        
        return headers
    read_headers = classmethod(read_headers)
    
    def read_lines_to_boundary(self, fp=None):
        endmarker = self.boundary + b"--"
        delim = b""
        prev_lf = True
        lines = []
        seen = 0
        while True:
            line = self.fp.readline(1<<16)
            if not line:
                raise EOFError("Illegal end of multipart body.")
            if line.startswith(b"--") and prev_lf:
                strippedline = line.strip()
                if strippedline == self.boundary:
                    break
                if strippedline == endmarker:
                    self.fp.done = True
                    break
            
            line = delim + line
            
            if line.endswith(b"\r\n"):
                delim = b"\r\n"
                line = line[:-2]
                prev_lf = True
            elif line.endswith(b"\n"):
                delim = b"\n"
                line = line[:-1]
                prev_lf = True
            else:
                delim = b""
                prev_lf = False
            
            if fp is None:
                lines.append(line)
                seen += len(line)
                if seen > self.maxrambytes:
                    fp = self.make_file()
                    for line in lines:
                        fp.write(line)
            else:
                fp.write(line)
        
        if fp is None:
            result = b''.join(lines)
            if self.encoding is not None:
                result = result.decode(self.encoding)
            return result
        else:
            fp.seek(0)
            return fp
    
    def default_proc(self):
        if self.filename:
            # Always read into a file if a .filename was given.
            self.file = self.read_into_file()
        else:
            result = self.read_lines_to_boundary()
            if isinstance(result, (bytes, str)):
                self.value = result
            else:
                self.file = result
    
    def read_into_file(self, fp=None):
        """Read the request body into fp (or make_file() if None). Return fp."""
        if fp is None:
            fp = self.make_file()
        self.read_lines_to_boundary(fp=fp)
        return fp


class SizedReader:
    
    def __init__(self, fp, length, maxbytes, bufsize=io.DEFAULT_BUFFER_SIZE):
        # Wrap our fp in a buffer so peek() works
        self.fp = fp
        self.length = length
        self.maxbytes = maxbytes
        self.buffer = b''
        self.bufsize = bufsize
        self.bytes_read = 0
        self.done = False
    
    def read(self, size=None, fp=None):
        """Read bytes from the request body and return or write them to a file.
        
        A number of bytes less than or equal to the 'size' argument are read
        off the socket. The actual number of bytes read are tracked in
        self.bytes_read. The number may be smaller than 'size' when 1) the
        client sends fewer bytes, 2) the 'Content-Length' request header
        specifies fewer bytes than requested, or 3) the number of bytes read
        exceeds self.maxbytes (in which case, MaxSizeExceeded is raised).
        
        If the 'fp' argument is None (the default), all bytes read are returned
        in a single byte string.
        
        If the 'fp' argument is not None, it must be a file-like object that
        supports the 'write' method; all bytes read will be written to the fp,
        and None is returned.
        """
        inf = float('inf')
        
        if self.length is None:
            if size is None:
                remaining = inf
            else:
                remaining = size
        else:
            remaining = self.length - self.bytes_read
            if size and size < remaining:
                remaining = size
        if remaining == 0:
            self.done = True
            return b'' if fp is None else None
        
        chunks = []
        
        # Read bytes from the buffer.
        if self.buffer:
            if remaining is inf:
                data = self.buffer
                self.buffer = b''
            else:
                data = self.buffer[:remaining]
                self.buffer = self.buffer[remaining:]
            datalen = len(data)
            remaining -= datalen
            
            # Check lengths.
            self.bytes_read += datalen
            if self.maxbytes and self.bytes_read > self.maxbytes:
                raise MaxSizeExceeded()
            
            # Store the data.
            if fp is None:
                chunks.append(data)
            else:
                fp.write(data)
        
        # Read bytes from the socket.
        while remaining > 0:
            chunksize = min(remaining, self.bufsize)
            data = self.fp.read(chunksize)
            if not data:
                self.done = True
                break
            datalen = len(data)
            remaining -= datalen
            
            # Check lengths.
            self.bytes_read += datalen
            if self.maxbytes and self.bytes_read > self.maxbytes:
                raise MaxSizeExceeded()
            
            # Store the data.
            if fp is None:
                chunks.append(data)
            else:
                fp.write(data)
        
        if fp is None:
            return b''.join(chunks)
    
    def readline(self, size=None):
        """Read a line from the request body and return it."""
        chunks = []
        while size is None or size > 0:
            chunksize = self.bufsize
            if size is not None and size < self.bufsize:
                chunksize = size
            data = self.read(chunksize)
            if not data:
                break
            pos = data.find(b'\n') + 1
            if pos:
                chunks.append(data[:pos])
                remainder = data[pos:]
                self.buffer += remainder
                self.bytes_read -= len(remainder)
                break
            else:
                chunks.append(data)
        return b''.join(chunks)
    
    def readlines(self, sizehint=None):
        """Read lines from the request body and return them."""
        if self.length is not None:
            if sizehint is None:
                sizehint = self.length - self.bytes_read
            else:
                sizehint = min(sizehint, self.length - self.bytes_read)
        
        lines = []
        seen = 0
        while True:
            line = self.readline()
            if not line:
                break
            lines.append(line)
            seen += len(line)
            if seen >= sizehint:
                break
        return lines


class RequestBody(Entity):
    
    # Don't parse the request body at all if the client didn't provide
    # a Content-Type header. See http://www.cherrypy.org/ticket/790
    default_content_type = ''
    
    default_encoding = 'utf-8'
    # http://www.w3.org/Protocols/rfc2616/rfc2616-sec3.html#sec3.7.1
    # When no explicit charset parameter is provided by the
    # sender, media subtypes of the "text" type are defined
    # to have a default charset value of "ISO-8859-1" when
    # received via HTTP.
    default_text_encoding = 'ISO-8859-1'
    bufsize = 8 * 1024
    maxbytes = None
    
    def __init__(self, fp, headers, params=None, request_params=None):
        Entity.__init__(self, fp, headers, params)
        self.fp = SizedReader(self.fp, self.length,
                              self.maxbytes, bufsize=self.bufsize)
        # Temporary fix while deprecating passing .parts as .params.
        self.processors['multipart'] = _old_process_multipart

        if request_params is None:
            request_params = {}
        self.request_params = request_params
        

    def process(self):
        """Include body params in request params."""
        # "The presence of a message-body in a request is signaled by the
        # inclusion of a Content-Length or Transfer-Encoding header field in
        # the request's message-headers."
        # It is possible to send a POST request with no body, for example;
        # however, app developers are responsible in that case to set
        # cherrypy.request.process_body to False so this method isn't called.
        h = cherrypy.request.headers
        if 'Content-Length' not in h and 'Transfer-Encoding' not in h:
            raise cherrypy.HTTPError(411)
        
        super(RequestBody, self).process()
        
        # Body params should also be a part of the request_params
        # add them in here.
        request_params = self.request_params
        for key, value in self.params.items():
            if key in request_params:
                if not isinstance(request_params[key], list):
                    request_params[key] = [request_params[key]]
                request_params[key].append(value)
            else:
                request_params[key] = value
