"""Regression test suite for CherryPy."""

import os
import sys


def newexit():
    """Handle Exit."""
    os._exit(1)


def setup():
    """Handle Setup.

    We want to monkey patch sys.exit so that we can get some
    information about where exit is being called.
    """
    newexit._old = sys.exit
    sys.exit = newexit


def teardown():
    """Handle Teardown."""
    try:
        sys.exit = sys.exit._old
    except AttributeError:
        sys.exit = sys._exit
