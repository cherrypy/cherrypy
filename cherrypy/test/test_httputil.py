"""Test helpers from ``cherrypy.lib.httputil`` module."""
import cherrypy
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
    ]
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
    ]
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
            r"Illegal response status from server \('hey' is non-numeric\)."
        ),
        (
            {'hey': 'hi'},
            r'Illegal response status from server '
            r"\(\{'hey': 'hi'\} is non-numeric\).",
        ),
        (1, r'Illegal response status from server \(1 is out of range\).'),
        (600, r'Illegal response status from server \(600 is out of range\).'),
    ]
)
def test_invalid_status(status_code, error_msg):
    """Check that invalid status cause certain errors."""
    with pytest.raises(ValueError, match=error_msg):
        httputil.valid_status(status_code)


@pytest.mark.parametrize(
    ('header_content', 'value', 'params'),
    (
        pytest.param(
            'application/x-www-form-urlencoded',
            'application/x-www-form-urlencoded',
            {},
            id='default-content-type',
        ),
        ('application/json;charset="utf8"',
         'application/json', {'charset': 'utf8'}),
        ('audio/*; q=0.2, audio/basic',
         'audio/*', {'q': '0.2, audio/basic'}),
        ('text/plain; q=0.5, text/html, text/x-dvi; q=0.8, text/x-c',
         'text/plain', {'q': '0.8, text/x-c'}),
        ('text/*, text/html, text/html;level=1, */*',
         'text/*, text/html, text/html', {'level': '1, */*'}),
        ('iso-8859-5, unicode-1-1;q=0.8',
         'iso-8859-5, unicode-1-1', {'q': '0.8'}),
        ('gzip;q=1.0, identity; q=0.5, *;q=0',
         'gzip', {'q': '0'}),
        ('da, en-gb;q=0.8, en;q=0.7',
         'da, en-gb', {'q': '0.7'}),
        ('text/plain',
         'text/plain', {}),
        ('text/xml',
         'text/xml', {}),
    ),
)
def test_header_element(header_content, value, params):
    """Test that ``value`` and ``params`` are extracted from headers.

    This is a positive test case, checking that the value and
    params are parsed from headers that are being passed into
    the :py:class:`~cherrypy.httputil.HeaderElement` class.
    """
    hdr_elem = httputil.HeaderElement.from_str(header_content)
    assert (hdr_elem.value, hdr_elem.params) == (value, params)


@pytest.mark.parametrize(
    ('header_content', 'media_type', 'qvalue'),
    (
        pytest.param(
            'application/x-www-form-urlencoded',
            'application/x-www-form-urlencoded',
            1.0,
            id='default-content-type',
        ),
        ('application/json;charset="utf8"',
         'application/json', 1.0),
        ('text/*, text/html, text/html;level=1, */*',
         'text/*, text/html, text/html', 1.0),
        ('iso-8859-5, unicode-1-1;q=0.8',
         'iso-8859-5, unicode-1-1', 0.8),
        ('text/plain',
         'text/plain', 1.0),
        ('text/xml',
         'text/xml', 1.0),
    ),
)
def test_accept_element(header_content, media_type, qvalue):
    """Test that ``value`` and ``qvalue`` are extracted from headers.

    This is being checked in the context of the
    :py:class:`~cherrypy.httputil.AcceptElement` class.
    """
    acc_elem = httputil.AcceptElement.from_str(header_content)
    assert (acc_elem.value, acc_elem.qvalue) == (media_type, qvalue)


@pytest.mark.parametrize(
    ('header_content', 'media_type', 'qvalue'),
    (
        ('audio/*; q=0.2, audio/basic',
         'audio/*', {'q': '0.2, audio/basic'}),
        ('text/plain; q=0.5, text/html, text/x-dvi; q=0.8, text/x-c',
         'text/plain', {'q': '0.8, text/x-c'}),
        ('gzip;q=1.0, identity; q=0.5, *;q=0',
         'gzip', {'q': '0'}),
        ('da, en-gb;q=0.8, en;q=0.7',
         'da, en-gb', 0.8),
    ),
)
def test_accept_element_raises_400(header_content, media_type, qvalue):
    """Check bad headers crash :class:`cherrypy.httputil.AcceptElement`.

    The expected exception is :exc:`~cherrypy.HTTPError`.
    """
    with pytest.raises(
            cherrypy.HTTPError,
            match=r'^Malformed HTTP header: `[^`]+`$',
    ):
        httputil.AcceptElement.from_str(header_content)
