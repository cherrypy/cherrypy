"""HTTP library functions."""

# This module contains functions for building an HTTP application
# framework: any one, not just one whose name starts with "Ch". ;) If you
# reference any modules from some popular framework inside *this* module,
# FuManChu will personally hang you up by your thumbs and submit you
# to a public caning.

from BaseHTTPServer import BaseHTTPRequestHandler
responseCodes = BaseHTTPRequestHandler.responses.copy()

# From http://www.cherrypy.org/ticket/361
responseCodes[500] = ('Internal error',
                      'The server encountered an unexpected condition '
                      'which prevented it from fulfilling the request.')
responseCodes[503] = ('Service Unavailable',
                      'The server is currently unable to handle the '
                      'request due to a temporary overloading or '
                      'maintenance of the server.')


import cgi
import re
import time
from urllib import unquote
from urlparse import urlparse


def urljoin(*atoms):
    url = "/".join(atoms)
    while "//" in url:
        url = url.replace("//", "/")
    return url


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


def version_from_http(version_str):
    """Return a Version tuple from the given 'HTTP/x.y' string."""
    return int(version_str[5]), int(version_str[7])

def getRanges(headervalue, content_length):
    """Return a list of (start, stop) indices from a Range header, or None.
    
    Each (start, stop) tuple will be composed of two ints, which are suitable
    for use in a slicing operation. That is, the header "Range: bytes=3-6",
    if applied against a Python string, is requesting resource[3:7]. This
    function will return the list [(3, 7)].
    """
    
    if not headervalue:
        return None
    
    result = []
    bytesunit, byteranges = headervalue.split("=", 1)
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
    
    return result


class HeaderElement(object):
    """An element (with parameters) from an HTTP header's element list."""
    
    def __init__(self, value, params=None):
        self.value = value
        if params is None:
            params = {}
        self.params = params
    
    def __str__(self):
        p = [";%s=%s" % (k, v) for k, v in self.params.iteritems()]
        return "%s%s" % (self.value, "".join(p))
    
    def parse(elementstr):
        """Transform 'token;key=val' to ('token', {'key': 'val'})."""
        # Split the element into a value and parameters. The 'value' may
        # be of the form, "token=token", but we don't split that here.
        atoms = [x.strip() for x in elementstr.split(";")]
        initial_value = atoms.pop(0).strip()
        params = {}
        for atom in atoms:
            atom = [x.strip() for x in atom.split("=", 1) if x.strip()]
            key = atom.pop(0)
            if atom:
                val = atom[0]
            else:
                val = ""
            params[key] = val
        return initial_value, params
    parse = staticmethod(parse)
    
    def from_str(cls, elementstr):
        """Construct an instance from a string of the form 'token;key=val'."""
        ival, params = cls.parse(elementstr)
        return cls(ival, params)
    from_str = classmethod(from_str)


class AcceptElement(HeaderElement):
    """An element (with parameters) from an Accept-* header's element list."""
    
    def from_str(cls, elementstr):
        qvalue = None
        # The first "q" parameter (if any) separates the initial
        # parameter(s) (if any) from the accept-params.
        atoms = re.split(r'; *q *=', elementstr, 1)
        initial_value = atoms.pop(0).strip()
        if atoms:
            # The qvalue for an Accept header can have extensions. The other
            # headers cannot, but it's easier to parse them as if they did.
            qvalue = HeaderElement.from_str(atoms[0].strip())
        
        ival, params = cls.parse(initial_value)
        if qvalue is not None:
            params["q"] = qvalue
        return cls(ival, params)
    from_str = classmethod(from_str)
    
    def qvalue(self):
        val = self.params.get("q", "1")
        if isinstance(val, HeaderElement):
            val = val.value
        return float(val)
    qvalue = property(qvalue, doc="The qvalue, or priority, of this value.")
    
    def __cmp__(self, other):
        # If you sort a list of AcceptElement objects, they will be listed
        # in priority order; the most preferred value will be first.
        diff = cmp(other.qvalue, self.qvalue)
        if diff == 0:
            diff = cmp(str(other), str(self))
        return diff


def header_elements(fieldname, fieldvalue):
    """Return a HeaderElement list from a comma-separated header str."""
    
    if not fieldvalue:
        return None
    headername = fieldname.lower()
    
    result = []
    for element in fieldvalue.split(","):
        if headername.startswith("accept") or headername == 'te':
            hv = AcceptElement.from_str(element)
        else:
            hv = HeaderElement.from_str(element)
        result.append(hv)
    
    result.sort()
    return result


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
        raise ValueError("Illegal response status from server "
                         "(%s is non-numeric)." % repr(code))
    
    if code < 100 or code > 599:
        raise ValueError("Illegal response status from server "
                         "(%s is out of range)." % repr(code))
    
    if code not in responseCodes:
        # code is unknown but not illegal
        defaultReason, message = "", ""
    else:
        defaultReason, message = responseCodes[code]
    
    if reason is None:
        reason = defaultReason
    
    return code, reason, message

def parse_request_line(request_line):
    """Return (method, path, querystring, protocol) from a request_line."""
    method, path, protocol = request_line.split()
    
    # path may be an abs_path (including "http://host.domain.tld");
    # Ignore scheme, location, and fragments (so config lookups work).
    # [Therefore, this assumes all hosts are valid for this server.
    # Note that we are also violating the RFC which says: if the host
    # given is an abs_path, it must override any Host header.]
    scheme, location, path, params, qs, frag = urlparse(path)
    
    if params:
        path = path + ";" + params
    
    # Unquote the path (e.g. "/this%20path" -> "this path").
    # http://www.w3.org/Protocols/rfc2616/rfc2616-sec5.html#sec5.1.2
    #
    # But note that "...a URI must be separated into its components
    # before the escaped characters within those components can be
    # safely decoded." http://www.ietf.org/rfc/rfc2396.txt, sec 2.4.2
    #
    # Note also that cgi.parse_qs will decode the querystring for us.
    atoms = [unquote(x) for x in re.split("(?i)%2F", path)]
    path = "%2F".join(atoms)
    
    return method, path, qs, protocol

def parseQueryString(query_string, keep_blank_values=True):
    """Build a paramMap dictionary from a query_string."""
    if re.match(r"[0-9]+,[0-9]+", query_string):
        # Server-side image map. Map the coords to 'x' and 'y'
        # (like CGI::Request does).
        pm = query_string.split(",")
        pm = {'x': int(pm[0]), 'y': int(pm[1])}
    else:
        pm = cgi.parse_qs(query_string, keep_blank_values)
        for key, val in pm.items():
            if len(val) == 1:
                pm[key] = val[0]
    return pm

def paramsFromCGIForm(form):
    paramMap = {}
    for key in form.keys():
        valueList = form[key]
        if isinstance(valueList, list):
            paramMap[key] = []
            for item in valueList:
                if item.filename is not None:
                    value = item # It's a file upload
                else:
                    value = item.value # It's a regular field
                paramMap[key].append(value)
        else:
            if valueList.filename is not None:
                value = valueList # It's a file upload
            else:
                value = valueList.value # It's a regular field
            paramMap[key] = value
    return paramMap


class CaseInsensitiveDict(dict):
    """A case-insensitive dict subclass.
    
    Each key is changed on entry to str(key).title().
    """
    
    def __getitem__(self, key):
        return dict.__getitem__(self, str(key).title())
    
    def __setitem__(self, key, value):
        dict.__setitem__(self, str(key).title(), value)
    
    def __delitem__(self, key):
        dict.__delitem__(self, str(key).title())
    
    def __contains__(self, key):
        return dict.__contains__(self, str(key).title())
    
    def get(self, key, default=None):
        return dict.get(self, str(key).title(), default)
    
    def has_key(self, key):
        return dict.has_key(self, str(key).title())
    
    def update(self, E):
        for k in E.keys():
            self[str(k).title()] = E[k]
    
    def fromkeys(cls, seq, value=None):
        newdict = cls()
        for k in seq:
            newdict[str(k).title()] = value
        return newdict
    fromkeys = classmethod(fromkeys)
    
    def setdefault(self, key, x=None):
        key = str(key).title()
        try:
            return self[key]
        except KeyError:
            self[key] = x
            return x
    
    def pop(self, key, default):
        return dict.pop(self, str(key).title(), default)


class HeaderMap(CaseInsensitiveDict):
    """A dict subclass for HTTP request and response headers.
    
    Each key is changed on entry to str(key).title(). This allows headers
    to be case-insensitive and avoid duplicates.
    """
    
    def elements(self, key):
        """Return a list of HeaderElements for the given header (or None)."""
        key = str(key).title()
        h = self.get(key)
        if h is None:
            return []
        return header_elements(key, h)
    
    general_fields = ["Cache-Control", "Connection", "Date", "Pragma",
                      "Trailer", "Transfer-Encoding", "Upgrade", "Via",
                      "Warning"]
    response_fields = ["Accept-Ranges", "Age", "ETag", "Location",
                       "Proxy-Authenticate", "Retry-After", "Server",
                       "Vary", "WWW-Authenticate"]
    entity_fields = ["Allow", "Content-Encoding", "Content-Language",
                     "Content-Length", "Content-Location", "Content-MD5",
                     "Content-Range", "Content-Type", "Expires",
                     "Last-Modified"]
    
    order_map = {}
    for _ in general_fields:
        order_map[_] = 0
    for _ in response_fields:
        order_map[_] = 1
    for _ in entity_fields:
        order_map[_] = 2
    
    def sorted_list(self):
        """Transform self into a sorted list of (name, value) tuples.
        
        From http://www.w3.org/Protocols/rfc2616/rfc2616-sec4.html#sec4.2
            '... it is "good practice" to send general-header fields first,
            followed by request-header or response-header fields, and ending
            with the entity-header fields.'
        """
        
        header_list = []
        for key, valueList in self.iteritems():
            order = self.order_map.get(key, 3)
            if not isinstance(valueList, list):
                valueList = [valueList]
            for value in valueList:
                header_list.append((order, (key, str(value))))
        header_list.sort()
        return [item[1] for item in header_list]


class MaxSizeExceeded(Exception):
    pass

class SizeCheckWrapper(object):
    """Wraps a file-like object, raising MaxSizeExceeded if too large."""
    
    def __init__(self, rfile, maxlen):
        self.rfile = rfile
        self.maxlen = maxlen
        self.bytes_read = 0
    
    def _check_length(self):
        if self.maxlen and self.bytes_read > self.maxlen:
            raise MaxSizeExceeded()
    
    def read(self, size = None):
        data = self.rfile.read(size)
        self.bytes_read += len(data)
        self._check_length()
        return data
    
    def readline(self, size = None):
        if size is not None:
            data = self.rfile.readline(size)
            self.bytes_read += len(data)
            self._check_length()
            return data
        
        # User didn't specify a size ...
        # We read the line in chunks to make sure it's not a 100MB line !
        res = []
        while True:
            data = self.rfile.readline(256)
            self.bytes_read += len(data)
            self._check_length()
            res.append(data)
            # See http://www.cherrypy.org/ticket/421
            if len(data) < 256 or data[-1:] == "\n":
                return ''.join(res)
    
    def readlines(self, sizehint = 0):
        # Shamelessly stolen from StringIO
        total = 0
        lines = []
        line = self.readline()
        while line:
            lines.append(line)
            total += len(line)
            if 0 < sizehint <= total:
                break
            line = self.readline()
        return lines
    
    def close(self):
        self.rfile.close()
    
    def __iter__(self):
        return self.rfile
    
    def next(self):
        data = self.rfile.next()
        self.bytes_read += len(data)
        self._check_length()
##      Normally the next method must raise StopIteration when it
##      fails but CP expects MaxSizeExceeded 
##        try:
##            self._check_length()
##        except:
##            raise StopIteration()
        return data

