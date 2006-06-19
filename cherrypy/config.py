"""Configuration system for CherryPy."""

import ConfigParser
import os

import cherrypy
from cherrypy.lib import autoreload, unrepr

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
        if other not in autoreload.reloadFiles:
            autoreload.reloadFiles.append(other)
        other = dict_from_config_file(other)
    elif hasattr(other, 'read'):
        other = dict_from_config_file(other)
    
    # Load other into base
    for section, value_map in other.iteritems():
        base.setdefault(section, {}).update(value_map)

default_conf = {
    'server.socket_port': 8080,
    'server.socket_host': '',
    'server.socket_file': '',
    'server.socket_queue_size': 5,
    'server.protocol_version': 'HTTP/1.0',
    'server.reverse_dns': False,
    'server.thread_pool': 10,
    'log_to_screen': True,
    'log_file': os.path.join(os.getcwd(), os.path.dirname(__file__),
                             "error.log"),
    'tools.log_tracebacks.on': True,
    'environment': "development",
    }

globalconf = default_conf.copy()

def reset():
    globalconf.clear()
    globalconf.update(default_conf)

def update(conf):
    """Update globalconf from a dict, file or filename."""
    if isinstance(conf, basestring):
        if conf not in autoreload.reloadFiles:
            autoreload.reloadFiles.append(conf)
        conf = dict_from_config_file(conf)
    elif hasattr(conf, 'read'):
        conf = dict_from_config_file(conf)
    if isinstance(conf.get("global", None), dict):
        conf = conf["global"]
    globalconf.update(conf)


def get(key, default=None):
    """Return the config value corresponding to key, or default."""
    
    try:
        conf = cherrypy.request.config
        if conf is None:
            conf = globalconf
    except AttributeError:
        # There's no request, so just use globalconf.
        conf = globalconf
    
    try:
        return conf[key]
    except KeyError:
        try:
            env = conf["environment"]
            return environments[env][key]
        except KeyError:
            return default


class CaseSensitiveConfigParser(ConfigParser.ConfigParser):
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

def dict_from_config_file(config_file, raw=False, vars=None):
    """Convert an INI file to a dictionary"""
    
    # Parse config file
    configParser = CaseSensitiveConfigParser()
    if hasattr(config_file, 'read'):
        configParser.readfp(config_file)
    else:
        configParser.read(config_file)
    
    # Load INI file into a dict
    result = {}
    for section in configParser.sections():
        if section not in result:
            result[section] = {}
        for option in configParser.options(section):
            value = configParser.get(section, option, raw, vars)
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


def output_config_map():
    """Log engine configuration parameters."""
    cherrypy.log("Server parameters:", 'CONFIG')
    
    serverVars = [
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
    
    for var in serverVars:
        cherrypy.log("  %s: %s" % (var, get(var)), 'CONFIG')

