"""Configuration system for CherryPy."""

import ConfigParser
import logging as _logging
_logfmt = _logging.Formatter("%(message)s")
import os as _os

import cherrypy


environments = {
    "development": {
        'autoreload.on': True,
        'log_file_not_found': True,
        'show_tracebacks': True,
        'log_request_headers': True,
        },
    "staging": {
        'autoreload.on': False,
        'log_file_not_found': False,
        'show_tracebacks': False,
        'log_request_headers': False,
        },
    "production": {
        'autoreload.on': False,
        'log_file_not_found': False,
        'show_tracebacks': False,
        'log_request_headers': False,
        },
    "embedded": {
        'autoreload.on': False,
        'log_to_screen': False,
        'server.class': None,
        },
    }

def merge(base, other):
    """Merge one app config (from a dict, file, or filename) into another."""
    if isinstance(other, basestring):
        if other not in cherrypy.engine.reload_files:
            cherrypy.engine.reload_files.append(other)
        other = Parser().dict_from_file(other)
    elif hasattr(other, 'read'):
        other = Parser().dict_from_file(other)
    
    # Load other into base
    for section, value_map in other.iteritems():
        # Resolve "environment" entries
        if 'environment' in value_map:
            env = environments[value_map['environment']]
            for k in env:
                if k not in value_map:
                    value_map[k] = env[k]
            del value_map['environment']
        
        base.setdefault(section, {}).update(value_map)

default_conf = {
    'server.socket_port': 8080,
    'server.socket_host': '',
    'server.socket_file': '',
    'server.socket_queue_size': 5,
    'server.socket_timeout': 10,
    'server.protocol_version': 'HTTP/1.0',
    'server.reverse_dns': False,
    'server.thread_pool': 10,
    'log_to_screen': True,
    'log_file': _os.path.join(_os.getcwd(), _os.path.dirname(__file__),
                              "error.log"),
    'tools.log_tracebacks.on': True,
    'environment': "development",
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
        conf = Parser().dict_from_file(conf)
    elif hasattr(conf, 'read'):
        conf = Parser().dict_from_file(conf)
    
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
    _configure_builtin_logging(globalconf, cherrypy._access_log, "log_access_file")

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

def _configure_builtin_logging(conf, log, filekey="log_file"):
    """Create/destroy builtin log handlers as needed from conf."""
    
    existing = dict([(getattr(x, "_cpbuiltin", None), x)
                     for x in log.handlers])
    h = existing.get("screen")
    screen = conf.get('log_to_screen')
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


class Parser(ConfigParser.ConfigParser):
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
                  'log_to_screen',
                  'log_file',
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
