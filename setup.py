"""Installs CherryPy using distutils

Run:
    python setup.py install

to install this package.
"""

from distutils.core import setup
from distutils.command.install import INSTALL_SCHEMES
import sys
import os
import shutil

required_python_version = '2.3'

###############################################################################
# arguments for the setup command
###############################################################################
name = "CherryPy"
version = "2.2.0beta"
desc = "Object-Oriented web development framework"
long_desc = "CherryPy is a pythonic, object-oriented web development framework"
classifiers=[
    #"Development Status :: 5 - Production/Stable",
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: Freely Distributable",
    "Programming Language :: Python",
    "Topic :: Internet ",
    "Topic :: Software Development :: Libraries :: Application Frameworks",
]
author="CherryPy Team"
author_email="team@cherrypy.org"
url="http://www.cherrypy.org"
cp_license="BSD"
packages=[
    "cherrypy", "cherrypy.lib", "cherrypy.lib.filter",
    "cherrypy.tutorial", "cherrypy.test", "cherrypy.filters",
]
download_url="http://sourceforge.net/project/showfiles.php?group_id=56099"
data_files=[
    ('cherrypy/tutorial',
        [
            'cherrypy/tutorial/tutorial.conf',
            'cherrypy/tutorial/README.txt',
            'cherrypy/tutorial/pdf_file.pdf',
            'cherrypy/tutorial/custom_error.html',
        ]
    ),
    ('cherrypy', ['cherrypy/favicon.ico',]),
    ('cherrypy/test', ['cherrypy/test/style.css',]),
    ('cherrypy/test/static', ['cherrypy/test/static/index.html',
                              'cherrypy/test/static/has space.html',]),
]
###############################################################################
# end arguments for setup
###############################################################################


def main():
    if sys.version < required_python_version:
        s = "I'm sorry, but %s %s requires Python %s or later."
        print s % (name, version, required_python_version)
        sys.exit(1)

    # set default location for "data_files" to platform specific "site-packages"
    # location
    for scheme in INSTALL_SCHEMES.values():
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
        packages=packages,
        download_url=download_url,
        data_files=data_files,
    )

    # the code in the following "if" block handles situations where the
    # user has installed over an older release of 2.1 with a conflicting
    # version of the sessionfilter
    if 'install_lib' in dist.command_obj:
        
        # get the installation directory (is there a better way to do this?)
        install_dir = dist.command_obj['install_lib'].install_dir

        # make sure we have an absolute install path
        install_dir = os.path.join(os.path.abspath('/'), install_dir)
        
        old_session_filter_path = os.path.join(
            install_dir, 'cherrypy', 'lib', 'filter', 'sessionfilter')
        
        # check for existence of old sessionfilter package dir
        # and prompt the user if it exists
        if os.path.exists(old_session_filter_path):
            handle_old_session_filter(old_session_filter_path)

        
def handle_old_session_filter(pth):
    warn_old_session_filter(pth)
    choice = raw_input('Delete old sessionfilter directory? (yes/no): ')
    if choice.lower() in ('y', 'yes'):
        shutil.rmtree(pth)
        print "Old sessionfilter directory deleted."
    else:
        print "You will need to manually need to delete the old sessionfilter directory."


def warn_old_session_filter(pth):
    msg = """
************************ WARNING *****************************
 Since you have installed over the top of an existing CherryPy
 installation, you must remove the old sessionfilter package
 directory at:
 %s
************************ WARNING *****************************
""" % (pth,)
    print msg
    

if __name__ == "__main__":
    main()
