#! /usr/bin/env python
"""CherryPy package setuptools installer."""

import io

import setuptools


###############################################################################
# arguments for the setup command
###############################################################################
name = 'CherryPy'
desc = 'Object-Oriented HTTP framework'

with io.open('README.rst', encoding='utf-8') as strm:
    long_desc = strm.read()

classifiers = [
    'Development Status :: 5 - Production/Stable',
    'Environment :: Web Environment',
    'Intended Audience :: Developers',
    'License :: Freely Distributable',
    'Operating System :: OS Independent',
    'Framework :: CherryPy',
    'License :: OSI Approved :: BSD License',
    'Programming Language :: Python',
    'Programming Language :: Python :: 2',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.1',
    'Programming Language :: Python :: 3.2',
    'Programming Language :: Python :: 3.3',
    'Programming Language :: Python :: 3.4',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: Implementation',
    'Programming Language :: Python :: Implementation :: CPython',
    'Programming Language :: Python :: Implementation :: Jython',
    'Programming Language :: Python :: Implementation :: PyPy',
    'Topic :: Internet :: WWW/HTTP',
    'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    'Topic :: Internet :: WWW/HTTP :: HTTP Servers',
    'Topic :: Internet :: WWW/HTTP :: WSGI',
    'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
    'Topic :: Internet :: WWW/HTTP :: WSGI :: Server',
    'Topic :: Software Development :: Libraries :: Application Frameworks',
]
author = 'CherryPy Team'
author_email = 'team@cherrypy.org'
url = 'http://www.cherrypy.org'
cp_license = 'BSD'
packages = [
    'cherrypy', 'cherrypy.lib',
    'cherrypy.tutorial', 'cherrypy.test',
    'cherrypy.process',
    'cherrypy.scaffold',
]

install_requires = [
    'six>=1.11.0',
    'cheroot>=5.8.3',
    'portend>=2.1.1',
    'jaraco.classes',
]

extras_require = {
    'docs': [
        'sphinx',
        'docutils',
        'alabaster',
        'rst.linker>=1.9',
        'jaraco.packaging>=3.2',
    ],
    'json': ['simplejson'],
    'routes_dispatcher': ['routes>=2.3.1'],
    'ssl': ['pyOpenSSL'],
    'testing': [
        'coverage',  # inspects tests coverage
        'codecov',   # sends tests coverage to codecov.io

        # cherrypy.lib.gctools
        'objgraph',

        'pytest>=2.8',
        'pytest-cov',
        'pytest-sugar',
        'backports.unittest_mock',
        'path.py',
    ],
    # Enables memcached session support via `cherrypy[memcached_session]`:
    'memcached_session': ['python-memcached>=1.58'],
    'xcgi': ['flup'],

    # http://docs.cherrypy.org/en/latest/advanced.html?highlight=windows#windows-console-events
    ':sys_platform == "win32"': ['pypiwin32'],
}
"""Feature flags end-users can use in dependencies"""

###############################################################################
# end arguments for setup
###############################################################################

setup_params = dict(
    name=name,
    use_scm_version=True,
    description=desc,
    long_description=long_desc,
    classifiers=classifiers,
    author=author,
    author_email=author_email,
    url=url,
    license=cp_license,
    packages=packages,
    entry_points={'console_scripts': ['cherryd = cherrypy.__main__:run']},
    include_package_data=True,
    install_requires=install_requires,
    extras_require=extras_require,
    setup_requires=[
        'setuptools_scm',
    ],
    python_requires='>=2.7,!=3.0.*',
)


def main():
    """Package installation entry point."""
    setuptools.setup(**setup_params)


if __name__ == '__main__':
    main()
