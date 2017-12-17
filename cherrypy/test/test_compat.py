"""Test Python 2/3 compatibility module."""
from __future__ import unicode_literals

import unittest

import pytest
import six

from cherrypy import _cpcompat as compat


class StringTester(unittest.TestCase):
    """Tests for string conversion."""

    @pytest.mark.skipif(six.PY3, reason='Only useful on Python 2')
    def test_ntob_native(self):
        s = compat.ntob(b'fight')
        assert isinstance(s, str), (
            'ntob should return a bytestring when given a bytestring')
        self.assertEqual(s, b'fight')

    @pytest.mark.skipif(six.PY3, reason='Only useful on Python 2')
    def test_ntob_non_native(self):
        """ntob should raise an Exception on unicode.

        (Python 2 only)

        See #1132 for discussion.
        """
        self.assertRaises(TypeError, compat.ntob, 'fight')

    def test_always_bytes_unicode(self):
        s = compat.always_bytes('fight')
        assert isinstance(s, str), (
            'always_bytes should return a bytestring when given unicode')
        self.assertEqual(s, 'fight')

    def test_always_bytes_already_bytes(self):
        nat = str('fight')
        s = compat.always_bytes(nat)
        assert s is nat, (
            'always_bytes should return its input when given a bytestring')

    def test_always_bytes_invalid_input(self):
        self.assertRaises(TypeError, compat.always_bytes, ['not a string'])


class EscapeTester(unittest.TestCase):
    """Class to test escape_html function from _cpcompat."""

    def test_escape_quote(self):
        """test_escape_quote - Verify the output for &<>"' chars."""
        self.assertEqual(
            """xx&amp;&lt;&gt;"aa'""",
            compat.escape_html("""xx&<>"aa'"""),
        )
