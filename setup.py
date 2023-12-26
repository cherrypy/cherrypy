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
    author_email='team@cherrypy.dev',
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
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
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
    url='https://www.cherrypy.dev',
    project_urls={
        'CI: AppVeyor': 'https://ci.appveyor.com/project/{}'.format(repo_slug),
        'CI: Travis': 'https://travis-ci.org/{}'.format(repo_slug),
        'CI: Circle': 'https://circleci.com/gh/{}'.format(repo_slug),
        'CI: GitHub': 'https://github.com/{}/actions'.format(repo_slug),
        'Docs: RTD': 'https://docs.cherrypy.dev',
        'GitHub: issues': '{}/issues'.format(repo_url),
        'GitHub: repo': repo_url,
        'Tidelift: funding':
        'https://tidelift.com/subscription/pkg/pypi-cherrypy'
        '?utm_source=pypi-cherrypy&utm_medium=referral&utm_campaign=pypi',
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
        'cheroot>=8.2.1',
        'portend>=2.1.1',
        'more_itertools',
        'zc.lockfile',
        'jaraco.collections',
        'importlib-metadata; python_version<="3.7"',
    ],
    extras_require={
        'docs': [
            'sphinx',
            'docutils',
            'alabaster',
            'sphinxcontrib-apidoc>=0.3.0',
            'rst.linker>=1.11',
            'jaraco.packaging>=3.2',
        ],
        'json': ['simplejson'],
        'routes_dispatcher': ['routes>=2.3.1'],
        'ssl': ['pyOpenSSL'],
        'testing': [
            # cherrypy.lib.gctools
            'objgraph',

            'pytest>=5.3.5',
            'pytest-cov',
            'pytest-forked',
            'pytest-sugar',
            'path.py',
            'requests_toolbelt',
            'pytest-services>=2',
            'setuptools',
        ],
        # Enables memcached session support via `cherrypy[memcached_session]`:
        'memcached_session': ['python-memcached>=1.58'],
        'xcgi': ['flup'],

        # https://docs.cherrypy.dev/en/latest/advanced.html?highlight=windows#windows-console-events
        ':sys_platform == "win32" and implementation_name == "cpython"'
        # pywin32 disabled while a build is unavailable. Ref #1920.
        ' and python_version < "3.10"': [
            'pywin32 >= 227',
        ],
    },
    setup_requires=[
        'setuptools_scm',
    ],
    python_requires='>=3.6',
)


__name__ == '__main__' and setuptools.setup(**params)
