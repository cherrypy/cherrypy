import unittest

import nose

from cherrypy import _cpcompat as compat


class StringTester(unittest.TestCase):
    def test_ntob_native(self):
        if compat.py3k:
            raise nose.SkipTest("Only useful on Python 2")
        s = compat.ntob('fight')
        assert isinstance(s, str), 'ntob should return a bytestring when given a bytestring'
        self.assertEqual(s, 'fight')

    def test_ntob_non_native(self):
        """
        ntob should raise an Exception on unicode.
        (Python 2 only)

        See #1132 for discussion.
        """
        if compat.py3k:
            raise nose.SkipTest("Only useful on Python 2")
        self.assertRaises(Exception, compat.ntob, unicode('fight'))

    def test_always_bytes_unicode(self):
        s = compat.always_bytes(compat.unicodestr('fight'))
        assert isinstance(s, compat.nativestr), 'always_bytes should return a bytestring when given unicode'
        self.assertEqual(s, 'fight')

    def test_always_bytes_already_bytes(self):
        nat = compat.nativestr('fight')
        s = compat.always_bytes(nat)
        assert s is nat, 'always_bytes should return its input when given a bytestring'

    def test_always_bytes_invalid_input(self):
        self.assertRaises(Exception, compat.always_bytes, ['not a string'])
