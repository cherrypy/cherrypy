"""
This script will walk a developer through the process of cutting a release.

Based on https://bitbucket.org/cherrypy/cherrypy/wiki/ReleaseProcess

To cut a release, simply invoke this script at the changeset to be released.
"""

from __future__ import print_function

import subprocess
import sys
import os
import platform
import shutil
import importlib

VERSION = '3.2.5'

if sys.version_info < (3,):
    input = raw_input


def get_next_version():
    print("The last release on this branch was {version}".format(
        version=VERSION))
    return input("What version are you releasing? ")

NEXT_VERSION = get_next_version()

files_with_versions = ('release.py', 'setup.py', 'cherrypy/__init__.py',
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


def check_status():
    """
    Make sure there aren't outstanding changesets that are unpushed, maybe
    run the tests or ask the user if the tests are passing.
    """
    print("You're about to release CherryPy {NEXT_VERSION}".format(
        **globals()))
    res = input('Have you run the tests with `nosetests -s ./` on '
                'Windows, Linux, and Mac on at least Python '
                '2.4, 2.5, 2.7, and 3.2? '
                .format(**globals()))
    if not res.lower().startswith('y'):
        print("Please do that")
        raise SystemExit(1)


def bump_versions():
    """
    Bump the versions in each of the places where it appears and commit.
    """
    list(map(bump_version, files_with_versions))

    subprocess.check_call(['hg', 'ci', '-m',
                           'Bumped to {NEXT_VERSION} in preparation for next '
                           'release.'.format(**globals())])


def bump_version(filename):
    with open(filename, 'rb') as f:
        b_version = VERSION.encode('ascii')
        b_next_version = NEXT_VERSION.encode('ascii')
        lines = [line.replace(b_version, b_next_version) for line in f]
    with open(filename, 'wb') as f:
        f.writelines(lines)


def tag_release():
    """
    Tag the release.
    """
    subprocess.check_call(['hg', 'tag', NEXT_VERSION])

dist_commands = ['sdist', 'bdist_wininst', 'bdist_wheel']


def build():
    if os.path.isfile('MANIFEST'):
        os.remove('MANIFEST')
    if os.path.isdir('dist'):
        shutil.rmtree('dist')
    subprocess.check_call([sys.executable, 'setup.py'] + dist_commands)


def push():
    "The build went well, so let's push the SCM changesets"
    subprocess.check_call(['hg', 'push', '-r', '.'])


def publish():
    """
    Publish the dists on PyPI
    """
    try:
        upload_dist_command = [sys.executable, 'setup.py'] + dist_commands + ['register', 'upload']
        subprocess.check_call(upload_dist_command)
    except:
        print("Unable to upload the dist files. Ask in IRC for help access 57"
              "or assistance.")
        raise SystemExit(4)
    print('Distributions have been uploaded.')
    print('Please ask in IRC for others to help you test '
          'CherryPy {NEXT_VERSION}.'
          .format(**globals()))
    print("Please confirm that the distro installs properly "
          "with `easy_install CherryPy=={NEXT_VERSION}`.".format(**globals()))


def announce():
    print("Please change the Wiki: Home page (news), CherryPyDownload")
    print("Please announce the release on newsgroups, mailing lists, "
          "and IRC /topic.")


def main():
    assert sys.version_info >= (2, 6), ("Release script requires Python 2.6 "
                                        "or later.")
    assert platform.system() == 'Windows', ('You must release on Windows '
                                            '(to create Windows installers)')
    check_wheel()
    check_status()
    bump_versions()
    tag_release()
    build()
    push()
    publish()
    announce()

if __name__ == '__main__':
    main()
