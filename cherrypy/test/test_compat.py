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
        s = compat.ntob(unicode('fight'))
        assert isinstance(s, str), 'ntob should return a bytestring when given unicode'
        self.assertEqual(s, 'fight')
