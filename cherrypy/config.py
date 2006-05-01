"""Configuration system for CherryPy."""

import ConfigParser
import os
_favicon_path = os.path.join(os.path.dirname(__file__), "favicon.ico")

import cherrypy
from cherrypy import _cputil
from cherrypy.lib import autoreload, cptools, httptools


# This configs dict holds the settings metadata for all cherrypy objects.
# Keys are URL paths, and values are dicts.
configs = {}

default_global = {
    'server.socket_port': 8080,
    'server.socket_host': '',
    'server.socket_file': '',
    'server.socket_queue_size': 5,
    'server.protocol_version': 'HTTP/1.0',
    'server.log_to_screen': True,
    'server.log_file': '',
    'tools.log_tracebacks.on': True,
    'server.reverse_dns': False,
    'server.thread_pool': 10,
    'server.environment': "development",
    
    '/favicon.ico': {'tools.staticfile.on': True,
                     'tools.staticfile.filename': _favicon_path},
    }

environments = {
    "development": {
        'autoreload.on': True,
        'server.log_file_not_found': True,
        'server.show_tracebacks': True,
        'server.log_request_headers': True,
        },
    "staging": {
        'autoreload.on': False,
        'server.log_file_not_found': False,
        'server.show_tracebacks': False,
        'server.log_request_headers': False,
        },
    "production": {
        'autoreload.on': False,
        'server.log_file_not_found': False,
        'server.show_tracebacks': False,
        'server.log_request_headers': False,
        },
    "embedded": {
        'autoreload.on': False,
        'server.log_to_screen': False,
        'server.init_only': True,
        'server.class': None,
        },
    }

def update(updateMap=None, file=None, overwrite=True, baseurl=""):
    """Update configs from a dictionary or a config file.
    
    If overwrite is False then the update will not modify values
    already defined in the configs.
    """
    if updateMap is None:
        updateMap = {}
    
    if file:
        if file not in autoreload.reloadFiles:
            autoreload.reloadFiles.append(file)
        updateMap = updateMap.copy()
        updateMap.update(dict_from_config_file(file))
    
    # Load new conf into cherrypy.configs
    for section, valueMap in updateMap.iteritems():
        # Handle shortcut syntax for "global" section
        #   example: update({'server.socket_port': 80})
        if not isinstance(valueMap, dict):
            valueMap = {section: valueMap}
            section = 'global'
        
        if baseurl and section.startswith("/"):
            if section == "/":
                section = baseurl
            else:
                section = httptools.urljoin(baseurl, section)
        
        bucket = configs.setdefault(section, {})
        if overwrite:
            bucket.update(valueMap)
        else:
            for key, value in valueMap.iteritems():
                bucket.setdefault(key, value)

def reset(useDefaults=True):
    """Clear configuration and restore defaults"""
    configs.clear()
    if useDefaults:
        update(default_global)
reset()

def get(key, default_value=None, return_section=False, path=None):
    """Return the configuration value corresponding to key
    If specified, return default_value on lookup failure. If return_section is
    specified, return the path to the value, instead of the value itself.
    """
    
    if path is None:
        try:
            path = cherrypy.request.object_path
        except AttributeError:
            # There's no request.object_path yet, so use the global settings.
            path = "global"
    
    while True:
        if path == "":
            path = "/"
        
        try:
            result = configs[path][key]
            break
        except KeyError:
            pass
        
        try:
            env = configs[path]["server.environment"]
            result = environments[env][key]
            break
        except KeyError:
            pass
        pass

        if path == "global":
            result = default_value
            break
        
        # Move one node up the tree and try again.
        if path == "/":
            path = "global"
        elif path in cherrypy.tree.mount_points:
            # We've reached the mount point for an application,
            # and should skip the rest of the tree (up to "global").
            path = "global"
        else:
            path = path[:path.rfind("/")]
    
    if return_section:
        return path
    else:
        return result

def request_config():
    """Return all configs in effect for the current request in a single dict."""
    path = cherrypy.request.object_path
    mounted_app_roots = cherrypy.tree.mount_points.values()
    
    # Convert the path into a list of names
    if (not path) or path == "*":
        nameList = []
    else:
        nameList = path.strip('/').split('/')
    nameList.append('index')
    
    curpath = ""
    node = cherrypy.root
    conf = getattr(node, "_cp_config", {}).copy()
    conf.update(configs.get("/", {}))
    for name in nameList:
        # Get _cp_config attached to each node on the cherrypy tree.
        objname = name.replace('.', '_')
        node = getattr(node, objname, None)
        if node is not None:
            if node in mounted_app_roots:
                # Dump and start over. This inefficiency should disappear
                # once we make cherrypy.localroot (specific to each request).
                conf = {}
            conf.update(getattr(node, "_cp_config", {}))
        
        # Get values from cherrypy.config for this path.
        curpath = "/".join((curpath, name))
        conf.update(configs.get(curpath, {}))
    
    base = configs.get("global", {}).copy()
    base.update(conf)
    return base


def request_config_section(key):
    """Return the (longest) path where the given key is defined (or None)."""
    path = cherrypy.request.object_path
    mounted_app_roots = cherrypy.tree.mount_points.values()
    
    # Convert the path into a list of names
    if (not path) or path == "*":
        nameList = []
    else:
        nameList = path.strip('/').split('/')
    nameList.append('index')
    
    foundpath = None
    
    curpath = ""
    node = cherrypy.root
    if key in getattr(node, "_cp_config", {}) or key in configs.get("/", {}):
        foundpath = "/"
    for name in nameList:
        # Get _cp_config attached to each node on the cherrypy tree.
        objname = name.replace('.', '_')
        node = getattr(node, objname, None)
        if node is not None:
            if node in mounted_app_roots:
                # Dump and start over. This inefficiency should disappear
                # once we make cherrypy.localroot (specific to each request).
                foundpath = None
            if key in getattr(node, "_cp_config", {}):
                foundpath = curpath or "/"
        
        # Get values from cherrypy.config for this path.
        curpath = "/".join((curpath, name))
        if key in configs.get(curpath, {}):
            foundpath = curpath
    
    if foundpath is None:
        foundpath = configs.get("global", {}).get(key)
    return foundpath


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

def dict_from_config_file(configFile, raw=False, vars=None):
    """Convert an INI file to a dictionary"""
    
    # Parse config file
    configParser = CaseSensitiveConfigParser()
    if hasattr(configFile, 'read'):
        configParser.readfp(configFile)
    else:
        configParser.read(configFile)
    
    # Load INI file into a dict
    result = {}
    for section in configParser.sections():
        if section not in result:
            result[section] = {}
        for option in configParser.options(section):
            value = configParser.get(section, option, raw, vars)
            try:
                value = cptools.unrepr(value)
            except Exception, x:
                msg = ("section: %s, option: %s, value: %s" %
                       (repr(section), repr(option), repr(value)))
                e = cherrypy.WrongConfigValue(msg)
                e.args += (x.__class__.__name__, x.args)
                raise e
            result[section][option] = value
    return result


def outputConfigMap():
    """Log server configuration parameters"""
    cherrypy.log("Server parameters:", 'CONFIG')
    
    serverVars = [
                  'server.environment',
                  'server.log_to_screen',
                  'server.log_file',
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

