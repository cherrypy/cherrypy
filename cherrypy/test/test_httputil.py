"""Test helpers from ``cherrypy.lib.httputil`` module."""

import pytest
import http.client

from cherrypy.lib import httputil


@pytest.mark.parametrize(
    'script_name,path_info,expected_url',
    [
        ('/sn/', '/pi/', '/sn/pi/'),
        ('/sn/', '/pi', '/sn/pi'),
        ('/sn/', '/', '/sn/'),
        ('/sn/', '', '/sn/'),
        ('/sn', '/pi/', '/sn/pi/'),
        ('/sn', '/pi', '/sn/pi'),
        ('/sn', '/', '/sn/'),
        ('/sn', '', '/sn'),
        ('/', '/pi/', '/pi/'),
        ('/', '/pi', '/pi'),
        ('/', '/', '/'),
        ('/', '', '/'),
        ('', '/pi/', '/pi/'),
        ('', '/pi', '/pi'),
        ('', '/', '/'),
        ('', '', '/'),
    ],
)
def test_urljoin(script_name, path_info, expected_url):
    """Test all slash+atom combinations for SCRIPT_NAME and PATH_INFO."""
    actual_url = httputil.urljoin(script_name, path_info)
    assert actual_url == expected_url


EXPECTED_200 = (200, 'OK', 'Request fulfilled, document follows')
EXPECTED_500 = (
    500,
    'Internal Server Error',
    'The server encountered an unexpected condition which '
    'prevented it from fulfilling the request.',
)
EXPECTED_404 = (404, 'Not Found', 'Nothing matches the given URI')
EXPECTED_444 = (444, 'Non-existent reason', '')


@pytest.mark.parametrize(
    'status,expected_status',
    [
        (None, EXPECTED_200),
        (200, EXPECTED_200),
        ('500', EXPECTED_500),
        (http.client.NOT_FOUND, EXPECTED_404),
        ('444 Non-existent reason', EXPECTED_444),
    ],
)
def test_valid_status(status, expected_status):
    """Check valid int, string and http.client-constants
    statuses processing."""
    assert httputil.valid_status(status) == expected_status


@pytest.mark.parametrize(
    'status_code,error_msg',
    [
        (
            'hey',
            r"Illegal response status from server \('hey' is non-numeric\).",
        ),
        (
            {'hey': 'hi'},
            r'Illegal response status from server '
            r"\(\{'hey': 'hi'\} is non-numeric\).",
        ),
        (1, r'Illegal response status from server \(1 is out of range\).'),
        (600, r'Illegal response status from server \(600 is out of range\).'),
    ],
)
def test_invalid_status(status_code, error_msg):
    """Check that invalid status cause certain errors."""
    with pytest.raises(ValueError, match=error_msg):
        httputil.valid_status(status_code)


def test_get_ranges_normal_cases():
    """Ordinary Range headers should be parsed as before."""
    assert httputil.get_ranges('bytes=3-6', 8) == [(3, 7)]
    assert httputil.get_ranges('bytes=2-4,-1', 8) == [(2, 5), (7, 8)]
    assert httputil.get_ranges('bytes=-100', 8) == [(0, 8)]
    assert httputil.get_ranges('', 8) is None
    assert httputil.get_ranges(None, 8) is None


def test_get_ranges_excessive_range_count_rejected():
    """
    Regression test for
    https://github.com/cherrypy/cherrypy/issues/1290

    A Range header specifying an excessive number of byte-ranges (e.g.
    many duplicate/overlapping small ranges over a large resource) can
    force the server to seek/read/emit the resource once per range,
    giving a small request disproportionate server-side cost -- the
    same class of issue as the well-known "Range header" DoS (e.g. CVE
    -2011-3192). get_ranges() should treat such a header as invalid
    (returning None, which callers already treat as "ignore the Range
    header and serve the full response") rather than returning an
    unbounded list of ranges.
    """
    content_length = 100000

    # At the limit: still honored normally.
    at_limit = 'bytes=' + ','.join(['1-2929'] * httputil.MAX_RANGES)
    result = httputil.get_ranges(at_limit, content_length)
    assert result is not None
    assert len(result) == httputil.MAX_RANGES

    # One over the limit: rejected.
    over_limit = 'bytes=' + ','.join(
        ['1-2929'] * (httputil.MAX_RANGES + 1)
    )
    assert httputil.get_ranges(over_limit, content_length) is None

    # A large attack-sized header is also rejected.
    many_ranges = 'bytes=' + ','.join(['1-2929'] * 1300)
    assert httputil.get_ranges(many_ranges, content_length) is None

    # Legitimate, small multi-range requests remain unaffected.
    assert httputil.get_ranges('bytes=0-99,200-299,400-499', content_length) == [
        (0, 100), (200, 300), (400, 500),
    ]

