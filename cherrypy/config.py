"""Configuration system for CherryPy."""

import ConfigParser

import cherrypy
from cherrypy import _cputil
from cherrypy.lib import autoreload, cptools


# This configMap dict holds the settings metadata for all cherrypy objects.
# Keys are URL paths, and values are dicts.
configMap = {}

defaultGlobal = {
    'server.socketPort': 8080,
    'server.socketHost': '',
    'server.socketFile': '',
    'server.socketQueueSize': 5,
    'server.protocolVersion': 'HTTP/1.0',
    'server.logToScreen': True,
    'server.logFile': '',
    'server.reverseDNS': False,
    'server.threadPool': 0,
    'server.environment': "development",
    }

environments = {
    "development": {
        'autoreload.on': True,
        'logDebugInfoFilter.on': True,
        'server.logFileNotFound': True,
        'server.showTracebacks': True,
        },
    "staging": {
        'autoreload.on': False,
        'logDebugInfoFilter.on': False,
        'server.logFileNotFound': False,
        'server.showTracebacks': False,
        },
    "production": {
        'autoreload.on': False,
        'logDebugInfoFilter.on': False,
        'server.logFileNotFound': False,
        'server.showTracebacks': False,
        },
    }

def update(updateMap=None, file=None, overwrite=True):
    """Update configMap from a dictionary or a config file.
    
    If overwrite is False then the update will not modify values
    already defined in the configMap.
    """
    if updateMap is None:
        updateMap = {}
    
    if file:
        if file not in autoreload.reloadFiles:
            autoreload.reloadFiles.append(file)
        updateMap = updateMap.copy()
        updateMap.update(dict_from_config_file(file))
    
    # Load new conf into cherrypy.configMap
    for section, valueMap in updateMap.iteritems():
        # Handle shortcut syntax for "global" section
        #   example: update({'server.socketPort': 80})
        if not isinstance(valueMap, dict):
            valueMap = {section: valueMap}
            section = 'global'
        
        bucket = configMap.setdefault(section, {})
        if overwrite:
            bucket.update(valueMap)
        else:
            for key, value in valueMap.iteritems():
                bucket.setdefault(key, value)

def reset(useDefaults=True):
    """Clear configuration and restore defaults"""
    configMap.clear()
    if useDefaults:
        update(defaultGlobal)
reset()

def get(key, defaultValue=None, returnSection=False, path = None):
    """Return the configuration value corresponding to key
    If specified, return defaultValue on lookup failure. If returnSection is
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
            result = configMap[path][key]
            break
        except KeyError:
            pass
        
        try:
            # Check for a server.environment entry at this node.
            env = configMap[path]["server.environment"]
            result = environments[env][key]
            break
        except KeyError:
            pass
        
        if path == "global":
            result = defaultValue
            break
        
        # Move one node up the tree and try again.
        if path == "/":
            path = "global"
        else:
            path = path[:path.rfind("/")]
    
    if returnSection:
        return path
    else:
        return result

def getAll(key):
    """Lookup key in the current node and all of its parent nodes
    as a list of path, value pairs.
    """
    # Needed by the session filter
    
    try:
        results = [('global', configMap['global'][key])]
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
            results.append((path, configMap[path][key]))
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
            except cherrypy.WrongUnreprValue, s:
                msg = ("section: %s, option: %s, value: %s" %
                       (repr(section), repr(option), repr(value)))
                raise cherrypy.WrongConfigValue(msg)
            result[section][option] = value
    return result


def outputConfigMap():
    """Log server configuration parameters"""
    cherrypy.log("Server parameters:", 'CONFIG')
    
    serverVars = [
                  'server.environment',
                  'server.logToScreen',
                  'server.logFile',
                  'server.protocolVersion',
                  'server.socketHost',
                  'server.socketPort',
                  'server.socketFile',
                  'server.reverseDNS',
                  'server.socketQueueSize',
                  'server.threadPool'
                 ]

    for var in serverVars:
        cherrypy.log("  %s: %s" % (var, get(var)), 'CONFIG')

