"""Regression test suite for CherryPy."""

import os
import sys


def newexit():
    """Exit the process with return code of 1."""
    os._exit(1)


def setup():
    """Monkey-patch ``sys.exit()``.
    # We want to monkey patch sys.exit so that we can get some
    # information about where exit is being called.
    newexit._old = sys.exit
    sys.exit = newexit


def teardown():
    """Recover the original ``sys.exit()``."""
    try:
        sys.exit = sys.exit._old
    except AttributeError:
        sys.exit = sys._exit
