"""
Regression test suite for CherryPy.
"""

import os
import sys

# for compatibility, expose cheroot webtest here
webtest = __import__('cheroot.test.webtest')


def newexit():
    os._exit(1)


def setup():
    # We want to monkey patch sys.exit so that we can get some
    # information about where exit is being called.
    newexit._old = sys.exit
    sys.exit = newexit


def teardown():
    try:
        sys.exit = sys.exit._old
    except AttributeError:
        sys.exit = sys._exit
