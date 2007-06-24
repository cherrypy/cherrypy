"""Tests for cherrypy/lib/http.py."""

from cherrypy.test import test
test.prefer_parent_path()

import unittest
from cherrypy.lib import http


class UtilityTests(unittest.TestCase):
    
    def test_urljoin(self):
        # Test all slash+atom combinations for SCRIPT_NAME and PATH_INFO
        self.assertEqual(http.urljoin("/sn/", "/pi/"), "/sn/pi/")
        self.assertEqual(http.urljoin("/sn/", "/pi"), "/sn/pi")
        self.assertEqual(http.urljoin("/sn/", "/"), "/sn/")
        self.assertEqual(http.urljoin("/sn/", ""), "/sn/")
        self.assertEqual(http.urljoin("/sn", "/pi/"), "/sn/pi/")
        self.assertEqual(http.urljoin("/sn", "/pi"), "/sn/pi")
        self.assertEqual(http.urljoin("/sn", "/"), "/sn/")
        self.assertEqual(http.urljoin("/sn", ""), "/sn")
        self.assertEqual(http.urljoin("/", "/pi/"), "/pi/")
        self.assertEqual(http.urljoin("/", "/pi"), "/pi")
        self.assertEqual(http.urljoin("/", "/"), "/")
        self.assertEqual(http.urljoin("/", ""), "/")
        self.assertEqual(http.urljoin("", "/pi/"), "/pi/")
        self.assertEqual(http.urljoin("", "/pi"), "/pi")
        self.assertEqual(http.urljoin("", "/"), "/")
        self.assertEqual(http.urljoin("", ""), "/")

if __name__ == '__main__':
    unittest.main()
