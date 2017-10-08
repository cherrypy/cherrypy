"""Tests for ``cherrypy.lib.httputil``."""
import pytest

from cherrypy.lib import httputil


class TestUtility(object):
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
    def test_urljoin(self, script_name, path_info, expected_url):
        """Test all slash+atom combinations for SCRIPT_NAME and PATH_INFO."""
        actual_url = httputil.urljoin(script_name, path_info)
        assert actual_url == expected_url
