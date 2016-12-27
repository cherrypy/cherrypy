import sys
import io

import setuptools


needs_pytest = set(['pytest', 'test']).intersection(sys.argv)
pytest_runner = ['pytest_runner'] if needs_pytest else []


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
    'Programming Language :: Python :: 2.6',
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
    'cherrypy.wsgiserver',
]
scripts = ['cherrypy/cherryd']

install_requires = [
    'six',
]

extras_require = {
    'doc': [
        'docutils',
        'sphinx_rtd_theme',
    ],
    'json': ['simplejson'],
    'routes_dispatcher': ['routes>=2.3.1'],
    'ssl': ['pyOpenSSL'],
    'testing': [
        'coverage',  # inspects tests coverage
        # TODO: drop nose dependency in favor of py.test analogue
        'nose',  # only used in cherrypy.test.{helper,test_{compat,routes}}
        'nose-testconfig',  # only used in cherrypy.test.helper
        'objgraph',  # cherrypy.lib.gctools
        'pytest',
        'backports.unittest_mock',
    ],
    # Enables memcached session support via `cherrypy[memcached_session]`:
    'memcached_session': ['python-memcached>=1.58'],
    'xcgi': ['flup'],

    # http://docs.cherrypy.org/en/latest/advanced.html?highlight=windows#windows-console-events
    # disabled on Python 3.6 due to #1537
    ':sys_platform == "win32" and python_version != "3.6"': ['pypiwin32'],
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
    scripts=scripts,
    include_package_data=True,
    install_requires=install_requires,
    extras_require=extras_require,
    setup_requires=[
        'setuptools_scm',
    ] + pytest_runner,
    python_requires='>=2.6,!=3.0.*',
)


def main():
    setuptools.setup(**setup_params)


if __name__ == '__main__':
    main()
