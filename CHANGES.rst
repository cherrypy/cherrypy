v8.7.0
-----

* #645: Setting a bind port of 0 will bind to an ephemeral port.

v8.6.0
-----

* #1538 and #1090: Removed cruft from the setup script and
  instead rely on `include_package_data
  <http://setuptools.readthedocs.io/en/latest/setuptools.html?highlight=include_package_data#new-and-changed-setup-keywords>`_
  to ensure the relevant files are included in the package.
  Note, this change does cause LICENSE.md no longer to
  be included in the installed package.

v8.5.0
-----

* The pyOpenSSL support is now included on Python 3 builds,
  removing the last disparity between Python 2 and Python 3
  in the CherryPy package. This change is one small step
  in consideration of #1399. This change also fixes RPM
  builds, as reported in #1149.

v8.4.0
-----

* #1532: Also release wheels for Python 2, enabling
  offline installation.

v8.3.1
-----

* #1537: Disable dependency on pypiwin32 on Python 3.6
  until a viable build of pypiwin32 can be made on that
  Python version.

v8.3.0
-----

* Consolidated some documentation and include the more
  concise readme in the package long description, as found
  on PyPI.

v8.2.0
-----

* #1463: CherryPy tests are now run under pytest and
  invoked using tox.

v8.1.3
-----

* #1530: Fix the issue with TypeError being swallowed by
  decorated handlers.

v8.1.2
-----

* #1508

v8.1.1
-----

* #1497: Handle errors thrown by ``ssl_module: 'builtin'``
  when client opens connection to HTTPS port using HTTP.

* #1350: Fix regression introduced in v6.1.0 where environment
  construction for WSGIGateway_u0 was passing one parameter
  and not two.

* Other miscellaneous fixes.

v8.1.0
-----

* #1473: ``HTTPError`` now also works as a context manager.

* #1487: The sessions tool now accepts a ``storage_class``
  parameter, which supersedes the new deprecated
  ``storage_type`` parameter. The ``storage_class`` should
  be the actual Session subclass to be used.

* Releases now use ``setuptools_scm`` to track the release
  versions. Therefore, releases can be cut by simply tagging
  a commit in the repo. Versions numbers are now stored in
  exactly one place.

v8.0.1
-----

* #1489 via #1493: Additionally reject anything else that's
  not bytes.
* #1492: systemd socket activation.

v8.0.0
-----

* #1483: Remove Deprecated constructs:

  - ``cherrypy.lib.http`` module.
  - ``unrepr``, ``modules``, and ``attributes`` in
    ``cherrypy.lib``.

* #1476: Drop support for python-memcached<1.58
* #1401: Handle NoSSLErrors.
* #1489: In ``wsgiserver.WSGIGateway.respond``, the application
  must now yield bytes and not text, as the spec requires.
  If text is received, it will now raise a ValueError instead
  of silently encoding using ISO-8859-1.
* Removed unicode filename from the package, working around
  pip #3894 and setuptools #704.

7.1.0
-----

# 1458: Implement systemd's socket activation mechanism for
  CherryPy servers, based on work sponsored by Endless Computers.

  Socket Activation allows one to setup a system so that
  systemd will sit on a port and start services
  'on demand' (a little bit like inetd and xinetd
  used to do).

7.0.0
-----

Removed the long-deprecated backward compatibility for
legacy config keys in the engine. Use the config for the
namespaced-plugins instead:

 - autoreload_on -> autoreload.on
 - autoreload_frequency -> autoreload.frequency
 - autoreload_match -> autoreload.match
 - reload_files -> autoreload.files
 - deadlock_poll_frequency -> timeout_monitor.frequency

6.2.1
-----

# 1460: Fix KeyError in Bus.publish when signal handlers
  set in config.

6.2.0
-----

* #1441: Added tool to automatically convert request
  params based on type annotations (primarily in
  Python 3). For example:

    @cherrypy.tools.params()
    def resource(self, limit: int):
        assert isinstance(limit, int)

6.1.1
-----

* Issue #1411: Fix issue where autoreload fails when
  the host interpreter for CherryPy was launched using
  ``python -m``.

6.1.0
-----

* Combined wsgiserver2 and wsgiserver3 modules into a
  single module, ``cherrypy.wsgiserver``.

6.0.2
-----

* Issue #1445: Correct additional typos.

6.0.1
-----

* Issue #1444: Correct typos in ``@cherrypy.expose``
  decorators.

6.0.0
-----

* Setuptools is now required to build CherryPy. Pure
  distutils installs are no longer supported. This change
  allows CherryPy to depend on other packages and re-use
  code from them. It's still possible to install
  pre-built CherryPy packages (wheels) using pip without
  Setuptools.
* `six <https://pypi.io/project/six>`_ is now a
  requirement and subsequent requirements will be
  declared in the project metadata.
* #1440: Back out changes from #1432 attempting to
  fix redirects with Unicode URLs, as it also had the
  unintended consequence of causing the 'Location'
  to be ``bytes`` on Python 3.
* ``cherrypy.expose`` now works on classes.
* ``cherrypy.config`` decorator is now used throughout
  the code internally.

5.6.0
-----

* ``@cherrypy.expose`` now will also set the exposed
  attribute on a class.
* Rewrote all tutorials and internal usage to prefer
  the decorator usage of ``expose`` rather than setting
  the attribute explicitly.
* Removed test-specific code from tutorials.

5.5.0
-----

* #1397: Fix for filenames with semicolons and quote
  characters in filenames found in headers.
* #1311: Added decorator for registering tools.
* #1194: Use simpler encoding rules for SCRIPT_NAME
  and PATH_INFO environment variables in CherryPy Tree
  allowing non-latin characters to pass even when
  ``wsgi.version`` is not ``u.0``.
* #1352: Ensure that multipart fields are decoded even
  when cached in a file.

5.4.0
-----

* ``cherrypy.test.webtest.WebCase`` now honors a
  'WEBTEST_INTERACTIVE' environment variable to disable
  interactive tests (still enabled by default). Set to '0'
  or 'false' or 'False' to disable interactive tests.
* #1408: Fix AttributeError when listiterator was accessed
  using the ``next`` attribute.
* #748: Removed ``cherrypy.lib.sessions.PostgresqlSession``.
* #1432: Fix errors with redirects to Unicode URLs.

5.3.0
-----

* #1202: Add support for specifying a certificate authority when
  serving SSL using the built-in SSL support.
* Use ssl.create_default_context when available.
* #1392: Catch platform-specific socket errors on OS X.
* #1386: Fix parsing of URIs containing ``://`` in the path part.

5.2.0
-----

* #1410: Moved hosting to Github (
  `cherrypy/cherrypy <https://github.com/cherrypy/cherrypy>`_.

5.1.0
-----

* Bugfix issue #1315 for ``test_HTTP11_pipelining`` test in Python 3.5
* Bugfix issue #1382 regarding the keyword arguments support for Python 3
  on the config file.
* Bugfix issue #1406 for ``test_2_KeyboardInterrupt`` test in Python 3.5.
  by monkey patching the HTTPRequest given a bug on CPython
  that is affecting the testsuite (https://bugs.python.org/issue23377).
* Add additional parameter ``raise_subcls`` to the tests helpers
  `openURL` and ``CPWebCase.getPage`` to have finer control on
  which exceptions can be raised.
* Add support for direct keywords on the calls (e.g. ``foo=bar``) on
  the config file under Python 3.
* Add additional validation to determine if the process is running
  as a daemon on ``cherrypy.process.plugins.SignalHandler`` to allow
  the execution of the testsuite under CI tools.

5.0.1
-----

* Bugfix for NameError following #94.

5.0.0
-----

* Removed deprecated support for ``ssl_certificate`` and
  ``ssl_private_key`` attributes and implicit construction
  of SSL adapter on Python 2 WSGI servers.
* Default SSL Adapter on Python 2 is the builtin SSL adapter,
  matching Python 3 behavior.
* Pull request #94: In proxy tool, defer to Host header for
  resolving the base if no base is supplied.

4.0.0
-----

* Drop support for Python 2.5 and earlier.
* No longer build Windows installers by default.

3.8.2
-----

* Pull Request #116: Correct InternalServerError when null bytes in
  static file path. Now responds with 404 instead.

3.8.0
-----

* Pull Request #96: Pass ``exc_info`` to logger as keyword rather than
  formatting the error and injecting into the message.

3.7.0
-----

* CherryPy daemon may now be invoked with ``python -m cherrypy`` in
  addition to the ``cherryd`` script.
* Issue #1298: Fix SSL handling on CPython 2.7 with builtin SSL module
  and pyOpenSSL 0.14. This change will break PyPy for now.
* Several documentation fixes.

3.6.0
-----

* Fixed HTTP range headers for negative length larger than content size.
* Disabled universal wheel generation as wsgiserver has Python duality.
* Pull Request #42: Correct TypeError in ``check_auth`` when encrypt is used.
* Pull Request #59: Correct signature of HandlerWrapperTool.
* Pull Request #60: Fix error in SessionAuth where login_screen was
  incorrectly used.
* Issue #1077: Support keyword-only arguments in dispatchers (Python 3).
* Issue #1019: Allow logging host name in the access log.
* Pull Request #50: Fixed race condition in session cleanup.

3.5.0
-----

* Issue #1301: When the incoming queue is full, now reject additional
  connections. This functionality was added to CherryPy 3.0, but
  unintentionally lost in 3.1.

3.4.0
-----

* Miscellaneous quality improvements.

3.3.0
-----

CherryPy adopts semver.
