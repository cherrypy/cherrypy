#! /usr/bin/env python
"""CherryPy package setuptools installer."""

import setuptools


name = 'CherryPy'
repo_slug = 'cherrypy/{}'.format(name.lower())
repo_url = 'https://github.com/{}'.format(repo_slug)


params = dict(
    name=name,
    use_scm_version=True,
    description='Object-Oriented HTTP framework',
    author='CherryPy Team',
    author_email='team@cherrypy.org',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: Freely Distributable',
        'Operating System :: OS Independent',
        'Framework :: CherryPy',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
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
    ],
    url='https://www.cherrypy.org',
    project_urls={
        'CI: AppVeyor': 'https://ci.appveyor.com/project/{}'.format(repo_slug),
        'CI: Travis': 'https://travis-ci.org/{}'.format(repo_slug),
        'CI: Circle': 'https://circleci.com/gh/{}'.format(repo_slug),
        'Docs: RTD': 'https://docs.cherrypy.org',
        'GitHub: issues': '{}/issues'.format(repo_url),
        'GitHub: repo': repo_url,
    },
    packages=[
        'cherrypy', 'cherrypy.lib',
        'cherrypy.tutorial', 'cherrypy.test',
        'cherrypy.process',
        'cherrypy.scaffold',
    ],
    entry_points={'console_scripts': ['cherryd = cherrypy.__main__:run']},
    include_package_data=True,
    install_requires=[
        'cheroot>=6.2.4',
        'portend>=2.1.1',
        'more_itertools',
        'zc.lockfile',
    ],
    extras_require={
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
        ],
        'testing:sys_platform != "win32"': [
            'pytest-services',
        ],
        # Enables memcached session support via `cherrypy[memcached_session]`:
        'memcached_session': ['python-memcached>=1.58'],
        'xcgi': ['flup'],

        # https://docs.cherrypy.org/en/latest/advanced.html?highlight=windows#windows-console-events
        ':sys_platform == "win32"': ['pywin32'],
    },
    setup_requires=[
        'setuptools_scm',
    ],
    python_requires='>=3.5',
)


__name__ == '__main__' and setuptools.setup(**params)
