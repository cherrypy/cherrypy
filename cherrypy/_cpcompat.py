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
strings to unicode strings.

Try not to use the compatibility functions 'ntob', 'ntou', 'tonative'.
They were created with Python 2.3-2.5 compatibility in mind.
Instead, use unicode literals (from __future__) and bytes literals
and their .encode/.decode methods as needed.
"""

import http.client


def _cgi_parseparam(s):
    while s[:1] == ';':
        s = s[1:]
        end = s.find(';')
        while end > 0 and (s.count('"', 0, end) - s.count('\\"', 0, end)) % 2:
            end = s.find(';', end + 1)
        if end < 0:
            end = len(s)
        f = s[:end]
        yield f.strip()
        s = s[end:]


def cgi_parse_header(line):
    """Parse a Content-type like header.

    Return the main content-type and a dictionary of options.

    Copied from removed stdlib cgi module. Couldn't find
    something to replace it with that provided same functionality
    from the email module as suggested.
    """
    parts = _cgi_parseparam(';' + line)
    key = parts.__next__()
    pdict = {}
    for p in parts:
        i = p.find('=')
        if i >= 0:
            name = p[:i].strip().lower()
            value = p[i + 1:].strip()
            if len(value) >= 2 and value[0] == value[-1] == '"':
                value = value[1:-1]
                value = value.replace('\\\\', '\\').replace('\\"', '"')
            pdict[name] = value
    return key, pdict


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


def assert_native(n):
    if not isinstance(n, str):
        raise TypeError('n must be a native str (got %s)' % type(n).__name__)


# Some platforms don't expose HTTPSConnection, so handle it separately
HTTPSConnection = getattr(http.client, 'HTTPSConnection', None)


text_or_bytes = str, bytes
