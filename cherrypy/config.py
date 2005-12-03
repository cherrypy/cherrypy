"""Configuration system for CherryPy."""

import ConfigParser

import cherrypy
from cherrypy import _cputil
from cherrypy.lib import autoreload, cptools


# This configs dict holds the settings metadata for all cherrypy objects.
# Keys are URL paths, and values are dicts.
configs = {}
configMap = configs # Backward compatibility

default_global = {
    'server.socket_port': 8080,
    'server.socket_host': '',
    'server.socket_file': '',
    'server.socket_queue_size': 5,
    'server.protocol_version': 'HTTP/1.0',
    'server.log_to_screen': True,
    'server.log_tracebacks': True,
    'server.log_file': '',
    'server.reverse_dns': False,
    'server.thread_pool': 0,
    'server.environment': "development",
    }

environments = {
    "development": {
        'autoreload.on': True,
        'log_debug_info_filter.on': True,
        'server.log_file_not_found': True,
        'server.show_tracebacks': True,
        'server.log_request_headers': True,
        },
    "staging": {
        'autoreload.on': False,
        'log_debug_info_filter.on': False,
        'server.log_file_not_found': False,
        'server.show_tracebacks': False,
        'server.log_request_headers': False,
        },
    "production": {
        'autoreload.on': False,
        'log_debug_info_filter.on': False,
        'server.log_file_not_found': False,
        'server.show_tracebacks': False,
        'server.log_request_headers': False,
        },
    }

def update(updateMap=None, file=None, overwrite=True):
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

def get(key, default_value=None, return_section=False, path = None):
    """Return the configuration value corresponding to key
    If specified, return default_value on lookup failure. If return_section is
    specified, return the path to the value, instead of the value itself.
    """
    # Look, ma, no Python function calls! Uber-fast.

    if path is None:
        try:
            path = cherrypy.request.objectPath
        except AttributeError:
            # There's no request.objectPath yet, so use the global settings.
            path = "global"
    
    while True:
        if path == "":
            path = "/"
        
        try:
            result = configs[path][_cputil.lower_to_camel(key)]
            break
        except KeyError:
            try:
                result = configs[path][key]
                break
            except KeyError:
                pass
            pass
        
        try:
            # Check for a server.environment entry at this node.
            env = configs[path]["server.environment"]
            # For backward compatibility, check for camelCase key first
            result = environments[env][_cputil.lower_to_camel(key)]
            break
        except KeyError:
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
        else:
            path = path[:path.rfind("/")]
    
    if return_section:
        return path
    else:
        return result

def getAll(key):
    """Lookup key in the current node and all of its parent nodes
    as a list of path, value pairs.
    """
    # Needed by the session filter
    
    try:
        results = [('global', configs['global'][key])]
    except KeyError:
        results = []
    
    try:
        path = cherrypy.request.objectPath
    except AttributeError:
        return results
    
    pathList = path.split('/')
    
    for n in xrange(1, len(pathList)):
        path = '/' + '/'.join(pathList[0:n+1])
        try:
            results.append((path, configs[path][key]))
        except KeyError:
            pass
    
    return results


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

def dict_from_config_file(configFile):
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
            value = configParser.get(section, option)
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
                  'server.log_tracebacks',
                  'server.log_request_headers',
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

