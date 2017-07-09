"""Compatibility code for using CherryPy with various versions of Python.

To retain compatibility with older Python versions, this module provides a
useful abstraction over the differences between Python versions, sometimes by
preferring a newer idiom, sometimes an older one, and sometimes a custom one.

In particular, Python 2 uses str and '' for byte strings, while Python 3
uses str and '' for unicode strings. We will call each of these the 'native
string' type for each version. Because of this major difference, this module
provides
two functions: 'ntob', which translates native strings (of type 'str') into
byte strings regardless of Python version, and 'ntou', which translates native
strings to unicode strings. This also provides a 'BytesIO' name for dealing
specifically with bytes, and a 'StringIO' name for dealing with native strings.
It also provides a 'base64_decode' function with native strings as input and
output.
"""

import re
import sys
import threading

import six
from six.moves import urllib

if six.PY3:
    def ntob(n, encoding='ISO-8859-1'):
        """Return the given native string as a byte string in the given
        encoding.
        """
        assert_native(n)
        # In Python 3, the native string type is unicode
        return n.encode(encoding)

    def ntou(n, encoding='ISO-8859-1'):
        """Return the given native string as a unicode string with the given
        encoding.
        """
        assert_native(n)
        # In Python 3, the native string type is unicode
        return n

    def tonative(n, encoding='ISO-8859-1'):
        """Return the given string as a native string in the given encoding."""
        # In Python 3, the native string type is unicode
        if isinstance(n, bytes):
            return n.decode(encoding)
        return n
else:
    # Python 2
    def ntob(n, encoding='ISO-8859-1'):
        """Return the given native string as a byte string in the given
        encoding.
        """
        assert_native(n)
        # In Python 2, the native string type is bytes. Assume it's already
        # in the given encoding, which for ISO-8859-1 is almost always what
        # was intended.
        return n

    def ntou(n, encoding='ISO-8859-1'):
        """Return the given native string as a unicode string with the given
        encoding.
        """
        assert_native(n)
        # In Python 2, the native string type is bytes.
        # First, check for the special encoding 'escape'. The test suite uses
        # this to signal that it wants to pass a string with embedded \uXXXX
        # escapes, but without having to prefix it with u'' for Python 2,
        # but no prefix for Python 3.
        if encoding == 'escape':
            return six.text_type(  # unicode for Python 2
                re.sub(r'\\u([0-9a-zA-Z]{4})',
                       lambda m: six.unichr(int(m.group(1), 16)),
                       n.decode('ISO-8859-1')))
        # Assume it's already in the given encoding, which for ISO-8859-1
        # is almost always what was intended.
        return n.decode(encoding)

    def tonative(n, encoding='ISO-8859-1'):
        """Return the given string as a native string in the given encoding."""
        # In Python 2, the native string type is bytes.
        if isinstance(n, six.text_type):  # unicode for Python 2
            return n.encode(encoding)
        return n


def assert_native(n):
    if not isinstance(n, str):
        raise TypeError('n must be a native str (got %s)' % type(n).__name__)


try:
    # Python 3.1+
    from base64 import decodebytes as _base64_decodebytes
except ImportError:
    # Python 3.0-
    # since CherryPy claims compability with Python 2.3, we must use
    # the legacy API of base64
    from base64 import decodestring as _base64_decodebytes


def base64_decode(n, encoding='ISO-8859-1'):
    """Return the native string base64-decoded (as a native string)."""
    if isinstance(n, six.text_type):
        b = n.encode(encoding)
    else:
        b = n
    b = _base64_decodebytes(b)
    if str is six.text_type:
        return b.decode(encoding)
    else:
        return b


try:
    # Python 3
    from urllib.parse import urljoin, urlencode
    from urllib.parse import quote, quote_plus
    from urllib.request import unquote, urlopen
    from urllib.request import parse_http_list, parse_keqv_list
except ImportError:
    # Python 2
    from urlparse import urljoin  # noqa
    from urllib import urlencode, urlopen  # noqa
    from urllib import quote, quote_plus  # noqa
    from urllib import unquote  # noqa
    from urllib2 import parse_http_list, parse_keqv_list  # noqa


# Some platforms don't expose HTTPSConnection, so handle it separately
HTTPSConnection = getattr(six.moves.http_client, 'HTTPSConnection', None)


def unquote_qs(atom, encoding, errors='strict'):
    atom_spc = atom.replace('+', ' ')
    return (
        urllib.parse.unquote(atom_spc, encoding=encoding, errors=errors)
        if six.PY3 else
        urllib.parse.unquote(atom_spc).decode(encoding, errors)
    )


try:
    # Prefer simplejson, which is usually more advanced than the builtin
    # module.
    import simplejson as json
    json_decode = json.JSONDecoder().decode
    _json_encode = json.JSONEncoder().iterencode
except ImportError:
    # json is part of the standard library
    import json
    json_decode = json.JSONDecoder().decode
    _json_encode = json.JSONEncoder().iterencode


if six.PY3:
    # Encode to bytes on Python 3
    def json_encode(value):
        for chunk in _json_encode(value):
            yield chunk.encode('utf-8')
else:
    json_encode = _json_encode


text_or_bytes = six.text_type, six.binary_type


if sys.version_info >= (3, 3):
    Timer = threading.Timer
    Event = threading.Event
else:
    # Python 3.2 and earlier
    Timer = threading._Timer
    Event = threading._Event

# html module come in 3.2 version
try:
    from html import escape
except ImportError:
    from cgi import escape

# html module needed the argument quote=False because in cgi the default
# is False. With quote=True the results differ.

def escape_html(s, escape_quote=False):  # noqa: E302
    """Replace special characters "&", "<" and ">" to HTML-safe sequences.

    When escape_quote=True, escape (') and (") chars.
    """
    return escape(s, quote=escape_quote)
