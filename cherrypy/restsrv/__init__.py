"""Manage an HTTP server process via an extensible Engine object.

An Engine object is used to contain and manage site-wide behavior:
daemonization, HTTP server instantiation, autoreload, signal handling,
drop privileges, initial logging, PID file management, etc.

In addition, an Engine object provides a place for each web framework
to hook in custom code that runs in response to site-wide events (like
process start and stop), or which controls or otherwise interacts with
the site-wide components mentioned above. For example, a framework which
uses file-based templates would add known template filenames to the
autoreload component.

Ideally, an Engine object will be flexible enough to be useful in a variety
of invocation scenarios:

 1. The deployer starts a site from the command line via a framework-
     neutral deployment script; applications from multiple frameworks
     are mixed in a single site. Command-line arguments and configuration
     files are used to define site-wide components such as the HTTP server,
     autoreload behavior, signal handling, etc.
 2. The deployer starts a site via some other process, such as Apache;
     applications from multiple frameworks are mixed in a single site.
     Autoreload and signal handling (from Python at least) are disabled.
 3. The deployer starts a site via a framework-specific mechanism;
     for example, when running tests, exploring tutorials, or deploying
     single applications from a single framework. The framework controls
     which site-wide components are enabled as it sees fit.

The Engine object in this package uses topic-based publish-subscribe
messaging to accomplish all this. A few topic channels are built in
('start', 'stop', 'restart' and 'graceful'). The 'plugins' module
defines a few others which are specific to each tool. Frameworks are
free to define their own. If a message is sent to a channel that has
not been defined or has no listeners, there is no effect.

In general, there should only ever be a single Engine object per process.
Frameworks share a single Engine object by publishing messages and
registering (subscribing) listeners.
"""

from cherrypy.restsrv import plugins

try:
    from cherrypy.restsrv import win32
    engine = win32.Engine()
except ImportError:
    from cherrypy.restsrv import base
    engine = base.Engine()
