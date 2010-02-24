"""Regression test suite for CherryPy.

Run test.py to exercise all tests.
"""

import sys
def newexit():
    raise SystemExit('Exit called')

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
