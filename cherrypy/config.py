"""Configuration system for CherryPy.

Configuration in CherryPy is implemented via dictionaries. Keys are strings
which name the mapped value, which may be of any type.


Architecture
------------

CherryPy Requests are part of an Application, which runs in a global context,
and configuration data may apply to any of those three scopes:

    Global: configuration entries which apply everywhere are stored in
    cherrypy.config.globalconf. Use the top-level function 'config.update'
    to modify it.
    
    Application: entries which apply to each mounted application are stored
    on the Application object itself, as 'app.conf'. This is a two-level
    dict where each key is a path, or "relative URL" (for example, "/" or
    "/path/to/my/page"), and each value is a config dict. Usually, this
    data is provided in the call to cherrypy.tree.mount(root(), conf=conf),
    although you may also use app.merge(conf).
    
    Request: each Request object possesses a single 'Request.config' dict.
    Early in the request process, this dict is populated by merging global
    config entries, Application entries (whose path equals or is a parent
    of Request.path_info), and any config acquired while looking up the
    page handler (see next).


Usage
-----

Configuration data may be supplied as a Python dictionary, as a filename,
or as an open file object. When you supply a filename or file, CherryPy
uses Python's builtin ConfigParser; you declare Application config by
writing each path as a section header:

    [/path/to/my/page]
    request.stream = True

To declare global configuration entries, place them in a [global] section.

You may also declare config entries directly on the classes and methods
(page handlers) that make up your CherryPy application via the '_cp_config'
attribute. For example:

    class Demo:
        _cp_config = {'tools.gzip.on': True}
        
        def index(self):
            raise cherrypy.InternalRedirect("/cuba")
        index.exposed = True
        index._cp_config = {'request.recursive_redirect': True}


Namespaces
----------

Configuration keys are separated into namespaces by the first "." in the key.
Current namespaces:

    autoreload: Controls the autoreload mechanism in cherrypy.engine.
                These can only be declared in the global config.
    deadlock:   Controls the deadlock monitoring system in cherrypy.engine.
                These can only be declared in the global config.
    hooks:      Declares additional request-processing functions.
    log:        Configures the logging for each application.
    request:    Adds attributes to each Request during the tool_up phase.
    response:   Adds attributes to each Response during the tool_up phase.
    server:     Controls the default HTTP server via cherrypy.server.
                These can only be declared in the global config.
    tools:      Runs and configures additional request-processing packages.

The only key that does not exist in a namespace is the "environment" entry.
This special entry 'imports' other config entries from a template stored in
cherrypy.config.environments[environment]. It only applies to globalconf,
and only when you use "update" to modify globalconf.
"""

import ConfigParser
import logging as _logging
_logfmt = _logging.Formatter("%(message)s")
import os as _os
_localdir = _os.path.dirname(__file__)

import cherrypy


environments = {
    "staging": {
        'autoreload.on': False,
        'tools.log_headers.on': False,
        'request.show_tracebacks': False,
        },
    "production": {
        'autoreload.on': False,
        'tools.log_headers.on': False,
        'request.show_tracebacks': False,
        'log.screen': False,
        },
    "test_suite": {
        'autoreload.on': False,
        'tools.log_headers.on': False,
        'request.show_tracebacks': True,
        'log.screen': False,
        },
    }

def merge(base, other):
    """Merge one app config (from a dict, file, or filename) into another."""
    if isinstance(other, basestring):
        if other not in cherrypy.engine.reload_files:
            cherrypy.engine.reload_files.append(other)
        other = _Parser().dict_from_file(other)
    elif hasattr(other, 'read'):
        other = _Parser().dict_from_file(other)
    
    # Load other into base
    for section, value_map in other.iteritems():
        base.setdefault(section, {}).update(value_map)


default_conf = {
    # Server config
    'server.socket_port': 8080,
    'server.socket_host': '',
    'server.socket_file': '',
    'server.socket_queue_size': 5,
    'server.socket_timeout': 10,
    'server.protocol_version': 'HTTP/1.1',
    'server.reverse_dns': False,
    'server.thread_pool': 10,
    'server.max_request_header_size': 500 * 1024,
    'server.instance': None,
    
    # Log config
    'log.to_screen': True,
##    'log.error.function': cherrypy._log_message,
    'log.error.file': _os.path.join(_os.getcwd(), _localdir, "error.log"),
    # Using an access file makes CP about 10% slower.
##    'log.access.function': cherrypy.log_access,
##    'log.access.file': _os.path.join(_os.getcwd(), _localdir, "access.log"),
    
    # Process management
    'autoreload.on': True,
    'autoreload.frequency': 1,
    'deadlock.timeout': 300,
    'deadlock.poll_freq': 60,
    
    'error_page.404': '',
    
    'tools.log_tracebacks.on': True,
    'tools.log_headers.on': True,
    }


globalconf = default_conf.copy()

def reset():
    globalconf.clear()
    update(default_conf)

def update(conf):
    """Update globalconf from a dict, file or filename."""
    if isinstance(conf, basestring):
        if conf not in cherrypy.engine.reload_files:
            cherrypy.engine.reload_files.append(conf)
        conf = _Parser().dict_from_file(conf)
    elif hasattr(conf, 'read'):
        conf = _Parser().dict_from_file(conf)
    
    if isinstance(conf.get("global", None), dict):
        conf = conf["global"]
    
    if 'environment' in conf:
        env = environments[conf['environment']]
        for k in env:
            if k not in conf:
                conf[k] = env[k]
    
    if 'tools.staticdir.dir' in conf:
        conf['tools.staticdir.section'] = "global"
    
    globalconf.update(conf)
    
    _configure_builtin_logging(globalconf, cherrypy._error_log)
    _configure_builtin_logging(globalconf, cherrypy._access_log, "log.access.file")

def _add_builtin_screen_handler(log):
    import sys
    h = _logging.StreamHandler(sys.stdout)
    h.setLevel(_logging.DEBUG)
    h.setFormatter(_logfmt)
    h._cpbuiltin = "screen"
    log.addHandler(h)

def _add_builtin_file_handler(log, fname):
    h = _logging.FileHandler(fname)
    h.setLevel(_logging.DEBUG)
    h.setFormatter(_logfmt)
    h._cpbuiltin = "file"
    log.addHandler(h)

def _configure_builtin_logging(conf, log, filekey="log.error.file"):
    """Create/destroy builtin log handlers as needed from conf."""
    
    existing = dict([(getattr(x, "_cpbuiltin", None), x)
                     for x in log.handlers])
    h = existing.get("screen")
    screen = conf.get('log.screen')
    if screen:
        if not h:
            _add_builtin_screen_handler(log)
    elif h:
        log.handlers.remove(h)
    
    h = existing.get("file")
    fname = conf.get(filekey)
    if fname:
        if h:
            if h.baseFilename != _os.path.abspath(fname):
                h.close()
                log.handlers.remove(h)
                _add_builtin_file_handler(log, fname)
        else:
            _add_builtin_file_handler(log, fname)
    else:
        if h:
            h.close()
            log.handlers.remove(h)

def get(key, default=None):
    """Return the config value corresponding to key, or default."""
    try:
        conf = cherrypy.request.config
        if conf is None:
            conf = globalconf
    except AttributeError:
        # There's no request, so just use globalconf.
        conf = globalconf
    
    return conf.get(key, default)


def wrap(**kwargs):
    """Decorator to set _cp_config on a handler using the given kwargs."""
    def wrapper(f):
        if not hasattr(f, "_cp_config"):
            f._cp_config = {}
        f._cp_config.update(kwargs)
        return f
    return wrapper


class _Parser(ConfigParser.ConfigParser):
    """Sub-class of ConfigParser that keeps the case of options and that raises
    an exception if the file cannot be read.
    """
    
    def optionxform(self, optionstr):
        return optionstr
    
    def read(self, filenames):
        if isinstance(filenames, basestring):
            filenames = [filenames]
        for filename in filenames:
            # try:
            #     fp = open(filename)
            # except IOError:
            #     continue
            fp = open(filename)
            try:
                self._read(fp, filename)
            finally:
                fp.close()
    
    def as_dict(self, raw=False, vars=None):
        """Convert an INI file to a dictionary"""
        # Load INI file into a dict
        from cherrypy.lib import unrepr
        result = {}
        for section in self.sections():
            if section not in result:
                result[section] = {}
            for option in self.options(section):
                value = self.get(section, option, raw, vars)
                try:
                    value = unrepr(value)
                except Exception, x:
                    msg = ("section: %s, option: %s, value: %s" %
                           (repr(section), repr(option), repr(value)))
                    e = cherrypy.WrongConfigValue(msg)
                    e.args += (x.__class__.__name__, x.args)
                    raise e
                result[section][option] = value
        return result
    
    def dict_from_file(self, file):
        if hasattr(file, 'read'):
            self.readfp(file)
        else:
            self.read(file)
        return self.as_dict()


def log_config():
    """Log engine configuration parameters."""
    cherrypy.log("Server parameters:", 'CONFIG')
    
    server_vars = [
                  'environment',
                  'log.screen',
                  'log.error.file',
                  'server.protocol_version',
                  'server.socket_host',
                  'server.socket_port',
                  'server.socket_file',
                  'server.reverse_dns',
                  'server.socket_queue_size',
                  'server.thread_pool',
                 ]
    
    for var in server_vars:
        cherrypy.log("  %s: %s" % (var, get(var)), 'CONFIG')


del ConfigParser
