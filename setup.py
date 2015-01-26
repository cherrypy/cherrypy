"""Installs CherryPy using distutils

Run:
    python setup.py install

to install this package.
"""

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

from distutils.command.install import INSTALL_SCHEMES
import sys


###############################################################################
# arguments for the setup command
###############################################################################
name = "CherryPy"
version = "4.0.0alpha"
desc = "Object-Oriented HTTP framework"
long_desc = "CherryPy is a pythonic, object-oriented HTTP framework"
classifiers = [
    "Development Status :: 3 - Alpha",
    "Environment :: Web Environment",
    "Intended Audience :: Developers",
    "License :: Freely Distributable",
    "Operating System :: OS Independent",
    "Framework :: CherryPy",
    "License :: OSI Approved :: BSD License",
    "Programming Language :: Python",
    "Programming Language :: Python :: 2",
    "Programming Language :: Python :: 2.7",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.3",
    "Programming Language :: Python :: Implementation",
    "Programming Language :: Python :: Implementation :: CPython",
    "Programming Language :: Python :: Implementation :: PyPy",
    "Topic :: Internet :: WWW/HTTP",
    "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
    "Topic :: Internet :: WWW/HTTP :: WSGI",
    "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
    "Topic :: Internet :: WWW/HTTP :: WSGI :: Server",
    "Topic :: Software Development :: Libraries :: Application Frameworks",
]
author = "CherryPy Team"
author_email = "team@cherrypy.org"
url = "http://www.cherrypy.org"
cp_license = "BSD"
packages = [
    "cherrypy", "cherrypy.lib", "cherrypy.lib.tools",
    "cherrypy.lib.tools.sessions", "cherrypy.lib.dispatch",
    "cherrypy.tutorial", "cherrypy.test",
    "cherrypy.scaffold",
]
data_files = [
    ('cherrypy', ['cherrypy/cherryd',
                  'cherrypy/favicon.ico',
                  'cherrypy/LICENSE.txt',
                  ]),
    ('cherrypy/scaffold', ['cherrypy/scaffold/example.conf',
                           'cherrypy/scaffold/site.conf',
                           ]),
    ('cherrypy/scaffold/static', [
        'cherrypy/scaffold/static/made_with_cherrypy_small.png']),
    ('cherrypy/test', ['cherrypy/test/style.css',
                       'cherrypy/test/test.pem',
                       ]),
    ('cherrypy/test/static', ['cherrypy/test/static/index.html',
                              'cherrypy/test/static/dirback.jpg', ]),
    ('cherrypy/tutorial',
        [
            'cherrypy/tutorial/tutorial.conf',
            'cherrypy/tutorial/README.txt',
            'cherrypy/tutorial/pdf_file.pdf',
            'cherrypy/tutorial/custom_error.html',
        ]
     ),
]
scripts = ["cherrypy/cherryd"]

if sys.version_info >= (3, 0):
    required_python_version = '3.3'
else:
    required_python_version = '2.7'

###############################################################################
# end arguments for setup
###############################################################################

# wininst may install data_files in Python/x.y instead of the cherrypy package.
# Django's solution is at http://code.djangoproject.com/changeset/8313
# See also
# http://mail.python.org/pipermail/distutils-sig/2004-August/004134.html
if 'bdist_wininst' in sys.argv or '--format=wininst' in sys.argv:
    data_files = [(r'\PURELIB\%s' % path, files) for path, files in data_files]


def main():
    if sys.version < required_python_version:
        s = "I'm sorry, but %s %s requires Python %s or later."
        print(s % (name, version, required_python_version))
        sys.exit(1)
    # set default location for "data_files" to
    # platform specific "site-packages" location
    for scheme in list(INSTALL_SCHEMES.values()):
        scheme['data'] = scheme['purelib']

    setup(
        name=name,
        version=version,
        description=desc,
        long_description=long_desc,
        classifiers=classifiers,
        author=author,
        author_email=author_email,
        url=url,
        license=cp_license,
        packages=packages,
        data_files=data_files,
        scripts=scripts,
        install_requires=[
            "magicbus>=4.0.0b1",
            "Cheroot>=4.0.0b2,!=4.0.0beta-20140210",
        ],
    )


if __name__ == "__main__":
    main()
