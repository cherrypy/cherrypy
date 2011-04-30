"""
Module that provides backward-compatible implementations of Python 2.5
built-in capability. Named py24compat because when you no longer need Python
2.4 compatibility, you can remove py24compat.
"""
import sys

def _partition_py24(s, sep):
    """ Returns a three element tuple, (head, sep, tail) where:

        head + sep + tail == s
        sep == '' or sep is t
        bool(sep) == (t in s)       # sep indicates if the string was found

    >>> s = 'http://www.python.org'
    >>> partition(s, '://')
    ('http', '://', 'www.python.org')
    >>> partition(s, '?')
    ('http://www.python.org', '', '')
    >>> partition(s, 'http://')
    ('', 'http://', 'www.python.org')
    >>> partition(s, 'org')
    ('http://www.python.', 'org', '')
    """
    if not isinstance(t, basestring) or not t:
        raise ValueError('partititon argument must be a non-empty string')
    parts = s.split(sep, 1)
    if len(parts) == 1:
        result = (s, '', '')
    else:
        result = (parts[0], sep, parts[1])
    assert len(result) == 3
    assert ''.join(result) == s
    assert result[1] == '' or result[1] is sep
    return result

if sys.version_info >= (2,5):
    partition = lambda s, sep: s.partition(sep)
else:
    partition = _partition_py24
