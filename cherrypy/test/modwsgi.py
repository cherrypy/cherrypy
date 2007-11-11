"""Wrapper for mod_wsgi, for use as a CherryPy HTTP server.

To autostart modwsgi, the "apache" executable or script must be
on your system path, or you must override the global APACHE_PATH.
On some platforms, "apache" may be called "apachectl" or "apache2ctl"--
create a symlink to them if needed.


KNOWN BUGS
==========

##1. Apache processes Range headers automatically; CherryPy's truncated
##    output is then truncated again by Apache. See test_core.testRanges.
##    This was worked around in http://www.cherrypy.org/changeset/1319.
2. Apache does not allow custom HTTP methods like CONNECT as per the spec.
    See test_core.testHTTPMethods.
3. Max request header and body settings do not work with Apache.
##4. Apache replaces status "reason phrases" automatically. For example,
##    CherryPy may set "304 Not modified" but Apache will write out
##    "304 Not Modified" (capital "M").
##5. Apache does not allow custom error codes as per the spec.
##6. Apache (or perhaps modpython, or modpython_gateway) unquotes %xx in the
##    Request-URI too early.
7. mod_wsgi will not read request bodies which use the "chunked"
    transfer-coding (it passes REQUEST_CHUNKED_ERROR to ap_setup_client_block
    instead of REQUEST_CHUNKED_DECHUNK, see Apache2's http_protocol.c and
    mod_python's requestobject.c).
8. When responding with 204 No Content, mod_wsgi adds a Content-Length
    header for you.
9. When an error is raised, mod_wsgi has no facility for printing a
    traceback as the response content (it's sent to the Apache log instead).
10. Startup and shutdown of Apache when running mod_wsgi seems slow.
"""

import os
curdir = os.path.join(os.getcwd(), os.path.dirname(__file__))
import re
import time

from cherrypy.test import test


def read_process(cmd, args=""):
    pipein, pipeout = os.popen4("%s %s" % (cmd, args))
    try:
        firstline = pipeout.readline()
        if (re.search(r"(not recognized|No such file|not found)", firstline,
                      re.IGNORECASE)):
            raise IOError('%s must be on your system path.' % cmd)
        output = firstline + pipeout.read()
    finally:
        pipeout.close()
    return output


APACHE_PATH = "apache"
CONF_PATH = "test_mw.conf"

conf_modwsgi = """
# Apache2 server conf file for testing CherryPy with modpython_gateway.

DocumentRoot "/"
Listen %%s
LoadModule wsgi_module modules/mod_wsgi.so
LoadModule env_module modules/mod_env.so

WSGIScriptAlias / %s
SetEnv testmod %%s
""" % os.path.join(curdir, 'modwsgi.py')


def start(testmod, port, conf_template):
    mpconf = CONF_PATH
    if not os.path.isabs(mpconf):
        mpconf = os.path.join(curdir, mpconf)
    
    f = open(mpconf, 'wb')
    try:
        f.write(conf_template % (port, testmod))
    finally:
        f.close()
    
    result = read_process(APACHE_PATH, "-k start -f %s" % mpconf)
    if result:
        print result

def stop():
    """Gracefully shutdown a server that is serving forever."""
    read_process(APACHE_PATH, "-k stop")


class ModWSGITestHarness(test.TestHarness):
    """TestHarness for ModWSGI and CherryPy."""
    
    use_wsgi = True
    
    def _run(self, conf):
        from cherrypy.test import webtest
        webtest.WebCase.PORT = self.port
        webtest.WebCase.harness = self
        webtest.WebCase.scheme = "http"
        webtest.WebCase.interactive = self.interactive
        print
        print "Running tests:", self.server
        
        conf_template = conf_modwsgi
        
        # mod_wsgi, since it runs in the Apache process, must be
        # started separately for each test, and then *that* process
        # must run the setup_server() function for the test.
        # Then our process can run the actual test.
        success = True
        for testmod in self.tests:
            try:
                start(testmod, self.port, conf_template)
                suite = webtest.ReloadingTestLoader().loadTestsFromName(testmod)
                result = webtest.TerseTestRunner(verbosity=2).run(suite)
                success &= result.wasSuccessful()
            finally:
                stop()
        if success:
            return 0
        else:
            return 1


loaded = False
def application(environ, start_response):
    import cherrypy
    global loaded
    if not loaded:
        loaded = True
        modname = "cherrypy.test." + environ['testmod']
        mod = __import__(modname, globals(), locals(), [''])
        mod.setup_server()
        
        cherrypy.config.update({
            "log.error_file": os.path.join(curdir, "test.log"),
            "environment": "test_suite",
            "engine.SIGHUP": None,
            "engine.SIGTERM": None,
            })
        cherrypy.server.unsubscribe()
        cherrypy.engine.start(blocking=False)
    return cherrypy.tree(environ, start_response)

