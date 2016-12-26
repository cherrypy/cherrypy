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
    return request.param


@pytest.fixture(autouse=True, scope="session")
def remove_sys_path_0():
    "pytest adds cwd to sys.path[0]"
    print("removing", sys.path[0])
    del sys.path[0]
    assert 'cherrypy' not in sys.modules


def test_data_files_installed(data_file_path):
    import cherrypy
    root = os.path.dirname(cherrypy.__file__)
    fn = os.path.join(root, data_file_path)
    assert os.path.exists(fn), fn
    # make sure the file isn't in the local checkout
    assert not os.path.samefile(fn, os.path.join('cherrypy', data_file_path))


def test_sanity():
    with pytest.raises(Exception):
        test_data_files_installed('does not exist')
