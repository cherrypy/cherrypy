"""
Use jaraco.packaging with this script to cut a release. After installing
jaraco.packaging, invoke:

python -m jaraco.packaging.release
"""

from __future__ import print_function

import sys
import os
import shutil
import importlib
import textwrap

files_with_versions = (
    'setup.py',
    'cherrypy/__init__.py',
    'cherrypy/wsgiserver/wsgiserver2.py',
    'cherrypy/wsgiserver/wsgiserver3.py',
)


def check_wheel():
    """
    Ensure 'wheel' is installed (required for bdist_wheel).
    """
    try:
        importlib.import_module('wheel')
    except ImportError:
        print("CherryPy requires 'wheel' be installed to produce wheels.",
              file=sys.stderr)
        raise SystemExit(5)


def before_upload():
    check_wheel()
    remove_files()

test_info = textwrap.dedent("""
    Run tests with `nosetests -s ./` on Windows, Linux, and Mac on at least
    Python 2.4, 2.5, 2.7, and 3.2.
    """).lstrip()

dist_commands = 'sdist', 'bdist_wininst', 'bdist_wheel'


def remove_files():
    if os.path.isfile('MANIFEST'):
        os.remove('MANIFEST')
    if os.path.isdir('dist'):
        shutil.rmtree('dist')


def announce():
    print('Distributions have been uploaded.')
    print('Please ask in IRC for others to help you test this release.')
    print("Please confirm that the distro installs properly "
          "with `easy_install CherryPy=={version}`.".format(**globals()))
    print("Please change the Wiki: Home page (news), CherryPyDownload")
    print("Please announce the release on newsgroups, mailing lists, "
          "and IRC /topic.")
