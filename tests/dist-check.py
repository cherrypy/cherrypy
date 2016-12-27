"""
Integration test to check the integrity of the
distribution.

This file is explicitly not named 'test_' to avoid
being collected by pytest, but must instead be
invoked explicitly (i.e. pytest tests/dist-check.py).

This test cannot be invoked as part of the normal
test suite nor can it be included in the normal test
suite because it must import cherrypy late (after
removing sys.path[0]).
"""

import os
import sys

import pytest


@pytest.fixture(params=[
    'favicon.ico',
    'scaffold/static/made_with_cherrypy_small.png',
    'tutorial/tutorial.conf',
    'tutorial/custom_error.html',
])
def data_file_path(request):
    "generates data file paths expected to be found in the package"
    return request.param


@pytest.fixture(autouse=True, scope="session")
def remove_sys_path_0():
    "pytest adds cwd to sys.path[0]"
    print("removing", sys.path[0])
    del sys.path[0]
    assert 'cherrypy' not in sys.modules


def test_data_files_installed(data_file_path):
    """
    Ensure that data file paths are available in the
    installed package as expected.
    """
    import cherrypy
    root = os.path.dirname(cherrypy.__file__)
    fn = os.path.join(root, data_file_path)
    assert os.path.exists(fn), fn
    # make sure the file isn't in the local checkout
    assert not os.path.samefile(fn, os.path.join('cherrypy', data_file_path))


def test_sanity():
    """
    Test the test to show that it does fail when a file
    is missing.
    """
    with pytest.raises(Exception):
        test_data_files_installed('does not exist')
