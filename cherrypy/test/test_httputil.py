"""Tests for ``cherrypy.lib.httputil``."""
import pytest
from six.moves import http_client

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


@pytest.mark.parametrize(
    'status,code,reason',
    [
        (None, 200, 'OK'),
        (200, 200, 'OK'),
        ('500', 500, 'Internal Server Error'),
        (http_client.NOT_FOUND, 404, 'Not Found'),
        ('444 Non-existent reason', 444, 'Non-existent reason'),
    ]
)
def test_valid_status(status, code, reason):
    """Valid int and string statuses."""
    assert httputil.valid_status(status)[:2] == (code, reason)


@pytest.mark.parametrize(
    'status_code,error_msg',
    [
        ('hey', "Illegal response status from server ('hey' is non-numeric)."),
        ({'hey': 'hi'}, "Illegal response status from server ({'hey': 'hi'} is non-numeric)."),
        (1, 'Illegal response status from server (1 is out of range).'),
        (600, 'Illegal response status from server (600 is out of range).'),
    ]
)
def test_invalid_status(status_code, error_msg):
    """Invalid status should raise an error."""
    with pytest.raises(ValueError) as excinfo:
        httputil.valid_status(status_code)

    assert error_msg in str(excinfo)
