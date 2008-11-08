"""Wrapper for mod_fcgid, for use as a CherryPy HTTP server when testing.

To autostart fcgid, the "apache" executable or script must be
on your system path, or you must override the global APACHE_PATH.
On some platforms, "apache" may be called "apachectl", "apache2ctl",
or "httpd"--create a symlink to them if needed.

You'll also need the WSGIServer from flup.servers.
See http://projects.amor.org/misc/wiki/ModPythonGateway


KNOWN BUGS
==========

1. Apache processes Range headers automatically; CherryPy's truncated
    output is then truncated again by Apache. See test_core.testRanges.
    This was worked around in http://www.cherrypy.org/changeset/1319.
2. Apache does not allow custom HTTP methods like CONNECT as per the spec.
    See test_core.testHTTPMethods.
3. Max request header and body settings do not work with Apache.
4. Apache replaces status "reason phrases" automatically. For example,
    CherryPy may set "304 Not modified" but Apache will write out
    "304 Not Modified" (capital "M").
5. Apache does not allow custom error codes as per the spec.
6. Apache (or perhaps modpython, or modpython_gateway) unquotes %xx in the
    Request-URI too early.
7. mod_python will not read request bodies which use the "chunked"
    transfer-coding (it passes REQUEST_CHUNKED_ERROR to ap_setup_client_block
    instead of REQUEST_CHUNKED_DECHUNK, see Apache2's http_protocol.c and
    mod_python's requestobject.c).
8. Apache will output a "Content-Length: 0" response header even if there's
    no response entity body. This isn't really a bug; it just differs from
    the CherryPy default.
"""

import os
curdir = os.path.join(os.getcwd(), os.path.dirname(__file__))
import re
import sys
import time

import cherrypy
from cherrypy.process import plugins, servers
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


APACHE_PATH = "httpd"
CONF_PATH = "fcgi.conf"

conf_fcgid = """
# Apache2 server conf file for testing CherryPy with mod_fcgid.

DocumentRoot "%(root)s"
Listen %(port)s
LoadModule fastcgi_module modules/mod_fastcgi.dll
LoadModule rewrite_module modules/mod_rewrite.so

Options ExecCGI
SetHandler fastcgi-script
RewriteEngine On
RewriteRule ^(.*)$ /fastcgi.pyc [L]
FastCgiExternalServer "%(server)s" -host 127.0.0.1:4000
"""

def start_apache(host, port, conf_template):
    fcgiconf = CONF_PATH
    if not os.path.isabs(fcgiconf):
        fcgiconf = os.path.join(curdir, fcgiconf)
    
    # Write the Apache conf file.
    f = open(fcgiconf, 'wb')
    try:
        server = repr(os.path.join(curdir, 'fastcgi.pyc'))[1:-1]
        output = conf_template % {'port': port, 'root': curdir,
                                  'server': server}
        output = output.replace('\r\n', '\n')
        f.write(output)
    finally:
        f.close()
    
    result = read_process(APACHE_PATH, "-k start -f %s" % fcgiconf)
    if result:
        print result

def stop():
    """Gracefully shutdown a server that is serving forever."""
    read_process(APACHE_PATH, "-k stop")


class FCGITestHarness(test.TestHarness):
    """TestHarness for fcgid and CherryPy."""
    
    def _run(self, conf):
        cherrypy.server.using_wsgi = True
        cherrypy.server.using_apache = True
        cherrypy.server.httpserver = servers.FlupFCGIServer(
            application=cherrypy.tree, bindAddress=('127.0.0.1', 4000))
        cherrypy.server.httpserver.bind_addr = ('127.0.0.1', 4000)
        try:
            start_apache(self.host, self.port, conf_fcgid)
            return test.TestHarness._run(self, conf)
        finally:
            stop()

