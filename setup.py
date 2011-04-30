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
import os

###############################################################################
# arguments for the setup command
###############################################################################
name = "CherryPy"
version = "3.2.1"
desc = "Object-Oriented HTTP framework"
long_desc = "CherryPy is a pythonic, object-oriented HTTP framework"
classifiers=[
    "Development Status :: 5 - Production/Stable",
    "Environment :: Web Environment",
    "Intended Audience :: Developers",
    "License :: Freely Distributable",
    "Operating System :: OS Independent",
    "Programming Language :: Python",
    "Programming Language :: Python :: 2",
    "Programming Language :: Python :: 3",
    "Topic :: Internet :: WWW/HTTP",
    "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
    "Topic :: Internet :: WWW/HTTP :: WSGI",
    "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
    "Topic :: Internet :: WWW/HTTP :: WSGI :: Server",
    "Topic :: Software Development :: Libraries :: Application Frameworks",
]
author="CherryPy Team"
author_email="team@cherrypy.org"
url="http://www.cherrypy.org"
cp_license="BSD"
packages=[
    "cherrypy", "cherrypy.lib",
    "cherrypy.tutorial", "cherrypy.test",
    "cherrypy.wsgiserver", "cherrypy.process",
    "cherrypy.scaffold",
]
download_url="http://download.cherrypy.org/cherrypy/3.2.0/"
data_files=[
    ('cherrypy', ['cherrypy/cherryd',
                  'cherrypy/favicon.ico',
                  'cherrypy/LICENSE.txt',
                  ]),
    ('cherrypy/process', []),
    ('cherrypy/scaffold', ['cherrypy/scaffold/example.conf',
                           'cherrypy/scaffold/site.conf',
                           ]),
    ('cherrypy/scaffold/static', ['cherrypy/scaffold/static/made_with_cherrypy_small.png',
                                  ]),
    ('cherrypy/test', ['cherrypy/test/style.css',
                       'cherrypy/test/test.pem',
                       ]),
    ('cherrypy/test/static', ['cherrypy/test/static/index.html',
                              'cherrypy/test/static/dirback.jpg',]),
    ('cherrypy/tutorial',
        [
            'cherrypy/tutorial/tutorial.conf',
            'cherrypy/tutorial/README.txt',
            'cherrypy/tutorial/pdf_file.pdf',
            'cherrypy/tutorial/custom_error.html',
        ]
    ),
]
if sys.version_info >= (3, 0):
    required_python_version = '3.0'
    setupdir = 'py3'
else:
    required_python_version = '2.3'
    setupdir = 'py2'
package_dir={'': setupdir}
data_files = [(install_dir, ['%s/%s' % (setupdir, f) for f in files])
              for install_dir, files in data_files]
scripts = ["%s/cherrypy/cherryd" % setupdir]

###############################################################################
# end arguments for setup
###############################################################################

def fix_data_files(data_files):
    """
    bdist_wininst seems to have a bug about where it installs data files.
    I found a fix the django team used to work around the problem at
    http://code.djangoproject.com/changeset/8313 .  This function
    re-implements that solution.
    Also see http://mail.python.org/pipermail/distutils-sig/2004-August/004134.html
    for more info.
    """
    def fix_dest_path(path):
        return '\\PURELIB\\%(path)s' % vars()
    
    if not 'bdist_wininst' in sys.argv: return
    
    data_files[:] = [
        (fix_dest_path(path), files)
        for path, files in data_files]
fix_data_files(data_files)

def main():
    if sys.version < required_python_version:
        s = "I'm sorry, but %s %s requires Python %s or later."
        print(s % (name, version, required_python_version))
        sys.exit(1)
    # set default location for "data_files" to
    # platform specific "site-packages" location
    for scheme in list(INSTALL_SCHEMES.values()):
        scheme['data'] = scheme['purelib']
    
    dist = setup(
        name=name,
        version=version,
        description=desc,
        long_description=long_desc,
        classifiers=classifiers,
        author=author,
        author_email=author_email,
        url=url,
        license=cp_license,
        package_dir=package_dir,
        packages=packages,
        download_url=download_url,
        data_files=data_files,
        scripts=scripts,
    )


if __name__ == "__main__":
    main()
