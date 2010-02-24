"""The actual script that runs the entire CP test suite.

There is a library of helper functions for the CherryPy test suite,
called "helper.py" (in this folder); this module calls that as a library.
"""

# GREAT CARE has been taken to separate this module from helper.py,
# because different consumers of each have mutually-exclusive import
# requirements. So don't go moving functions from here into helper.py,
# or vice-versa, unless you *really* know what you're doing.


import getopt
from httplib import HTTPSConnection
import os
localDir = os.path.dirname(__file__)
serverpem = os.path.join(os.getcwd(), localDir, 'test.pem')
import sys
import warnings
import cherrypy
from cherrypy.test import webtest
from cherrypy.lib.reprconf import unrepr

_testconfig = None

def get_tst_config(overconf = {}):
    global _testconfig
    if _testconfig is None:
        conf = {
            'scheme': 'http',
            'protocol': "HTTP/1.1",
            'port': 8080,
            'host': '127.0.0.1',
            'validate': False,
            'conquer': False,
        }
        try:
            import testconfig
            _conf = testconfig.config.get('supervisor', None)
            if _conf is not None:
                for k, v in _conf.iteritems():
                    if isinstance(v, basestring):
                        _conf[k] = unrepr(v)
                conf.update(_conf)
        except ImportError:
            pass
        _testconfig = conf
    conf = _testconfig.copy()
    conf.update(overconf)

    return conf

class Supervisor(object):
    """Base class for modeling and controlling servers during testing."""

    def __init__(self, **kwargs):
        for k, v in kwargs.iteritems():
            if k == 'port':
                setattr(self, k, int(v))
            setattr(self, k, v)


class LocalSupervisor(Supervisor):
    """Base class for modeling/controlling servers which run in the same process.

    When the server side runs in a different process, start/stop can dump all
    state between each test module easily. When the server side runs in the
    same process as the client, however, we have to do a bit more work to ensure
    config and mounted apps are reset between tests.
    """

    using_apache = False
    using_wsgi = False

    def __init__(self, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)

        cherrypy.server.httpserver = self.httpserver_class

        engine = cherrypy.engine
        if hasattr(engine, "signal_handler"):
            engine.signal_handler.subscribe()
        if hasattr(engine, "console_control_handler"):
            engine.console_control_handler.subscribe()
        #engine.subscribe('log', lambda msg, level: sys.stderr.write(msg + os.linesep))

    def start(self, modulename=None):
        """Load and start the HTTP server."""
        if modulename:
            # Unhook httpserver so cherrypy.server.start() creates a new
            # one (with config from setup_server, if declared).
            cherrypy.server.httpserver = None

        cherrypy.engine.start()

        self.sync_apps()

    def sync_apps(self):
        """Tell the server about any apps which the setup functions mounted."""
        pass

    def stop(self):
        td = getattr(self, 'teardown', None)
        if td:
            td()
        cherrypy.engine.exit()


class NativeServerSupervisor(LocalSupervisor):
    """Server supervisor for the builtin HTTP server."""

    httpserver_class = "cherrypy._cpnative_server.CPHTTPServer"
    using_apache = False
    using_wsgi = False

    def __str__(self):
        return "Builtin HTTP Server on %s:%s" % (self.host, self.port)


class LocalWSGISupervisor(LocalSupervisor):
    """Server supervisor for the builtin WSGI server."""

    httpserver_class = "cherrypy._cpwsgi_server.CPWSGIServer"
    using_apache = False
    using_wsgi = True

    def __str__(self):
        return "Builtin WSGI Server on %s:%s" % (self.host, self.port)

    def sync_apps(self):
        """Hook a new WSGI app into the origin server."""
        cherrypy.server.httpserver.wsgi_app = self.get_app()

    def get_app(self):
        """Obtain a new (decorated) WSGI app to hook into the origin server."""
        app = cherrypy.tree
        if self.conquer:
            try:
                import wsgiconq
            except ImportError:
                warnings.warn("Error importing wsgiconq. pyconquer will not run.")
            else:
                app = wsgiconq.WSGILogger(app, c_calls=True)
        if self.validate:
            try:
                from wsgiref import validate
            except ImportError:
                warnings.warn("Error importing wsgiref. The validator will not run.")
            else:
                #wraps the app in the validator
                app = validate.validator(app)

        return app


def get_cpmodpy_supervisor(**options):
    from cherrypy.test import modpy
    sup = modpy.ModPythonSupervisor(**options)
    sup.template = modpy.conf_cpmodpy
    return sup

def get_modpygw_supervisor(**options):
    from cherrypy.test import modpy
    sup = modpy.ModPythonSupervisor(**options)
    sup.template = modpy.conf_modpython_gateway
    sup.using_wsgi = True
    return sup

def get_modwsgi_supervisor(**options):
    from cherrypy.test import modwsgi
    return modwsgi.ModWSGISupervisor(**options)

def get_modfcgid_supervisor(**options):
    from cherrypy.test import modfcgid
    return modfcgid.ModFCGISupervisor(**options)

def get_wsgi_u_supervisor(**options):
    cherrypy.server.wsgi_version = ('u', 0)
    return LocalWSGISupervisor(**options)
