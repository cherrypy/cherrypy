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
url = 'https://www.cherrypy.org'
repo_slug = 'cherrypy/{}'.format(name)
repo_url = 'https://github.com/{}'.format(repo_slug)
cp_license = 'BSD'
packages = [
    'cherrypy', 'cherrypy.lib',
    'cherrypy.tutorial', 'cherrypy.test',
    'cherrypy.process',
    'cherrypy.scaffold',
]

# install requirements must not contain namespace
# packages. See #1673
install_requires = [
    'six>=1.11.0',
    'cheroot>=6.2.4',
    'portend>=2.1.1',

    # temporary workaround for #1722
    'tempora<1.13',
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
        'requests_toolbelt',
        'jaraco.packaging',
    ],
    # Enables memcached session support via `cherrypy[memcached_session]`:
    'memcached_session': ['python-memcached>=1.58'],
    'xcgi': ['flup'],

    # https://docs.cherrypy.org/en/latest/advanced.html?highlight=windows#windows-console-events
    ':sys_platform == "win32" and python_version != "3.4"': ['pywin32'],
    ':sys_platform == "win32" and python_version == "3.4"': ['pypiwin32==219'],
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
    project_urls={
        'CI: AppVeyor': 'https://ci.appveyor.com/project/{}'.format(repo_slug),
        'CI: Travis': 'https://travis-ci.org/{}'.format(repo_slug),
        'CI: Circle': 'https://circleci.com/gh/{}'.format(repo_slug),
        'Docs: RTD': 'https://docs.cherrypy.org',
        'GitHub: issues': '{}/issues'.format(repo_url),
        'GitHub: repo': repo_url,
    },
    license=cp_license,
    packages=packages,
    entry_points={'console_scripts': ['cherryd = cherrypy.__main__:run']},
    include_package_data=True,
    install_requires=install_requires,
    extras_require=extras_require,
    setup_requires=[
        'setuptools_scm',
    ],
    python_requires='>=2.7,!=3.0.*,!=3.1.*,!=3.2.*,!=3.3.*',
)


def main():
    """Run setup as a package installation entry point."""
    setuptools.setup(**setup_params)


if __name__ == '__main__':
    main()
