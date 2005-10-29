"""
Copyright (c) 2004, CherryPy Team (team@cherrypy.org)
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, 
are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice, 
      this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice, 
      this list of conditions and the following disclaimer in the documentation 
      and/or other materials provided with the distribution.
    * Neither the name of the CherryPy Team nor the names of its contributors 
      may be used to endorse or promote products derived from this software 
      without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND 
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED 
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE 
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE 
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL 
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR 
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER 
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, 
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE 
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

"""
Configuration system for CherryPy.
"""

import ConfigParser

import cherrypy
from cherrypy import _cputil, _cperror
from cherrypy.lib import autoreload


# This configMap dict holds the settings metadata for all cherrypy objects.
# Keys are URL paths, and values are dicts.
configMap = {}

defaultGlobal = {
    'server.socketPort': 8080,
    'server.socketHost': '',
    'server.socketFile': '',
    'server.socketQueueSize': 5,
    
    'server.environment': 'development',
    'server.protocolVersion': 'HTTP/1.0',
    'server.logToScreen': True,
    'server.logFile': '',
    'server.reverseDNS': False,
    'server.threadPool': 0,
    }

def reset(useDefaults=True):
    """Clear configuration and restore defaults"""
    configMap.clear()
    if useDefaults:
        configMap["global"] = defaultGlobal.copy()
reset()

def update(updateMap=None, file=None, override=True):
    """Update configMap from a dictionary or a config file
    If override is True then the update will not modify values already defined
    in the configMap.
    """
    if updateMap:
        for section, valueMap in updateMap.iteritems():
            if not isinstance(valueMap, dict):
                # Shortcut syntax
                #   ex: update({'server.socketPort': 80})
                valueMap = {section: valueMap}
                section = 'global'
            sectionMap = configMap.setdefault(section, {})
            if override:
                sectionMap.update(valueMap)
            else:
                for key, value in valueMap.iteritems():
                    sectionMap.setdefault(key, value)
    if file:
        if file not in autoreload.reloadFiles:
            autoreload.reloadFiles.append(file)
        _load(file, override)

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
        except KeyError:
            if path == "global":
                result = defaultValue
            elif path == "/":
                path = "global"
                continue
            else:
                path = path[:path.rfind("/")]
                continue
        break
    
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
                value = _cputil.unrepr(value)
            except _cperror.WrongUnreprValue, s:
                msg = ("section: %s, option: %s, value: %s" %
                       (repr(section), repr(option), repr(value)))
                raise _cperror.WrongConfigValue(msg)
            result[section][option] = value
    return result


def _load(configFile, override=True):
    """Merge an INI file into configMap
    If override is false, preserve values already in the configMap.
    """
    
    conf = dict_from_config_file(configFile)
    
    # Load new conf into cherrypy.configMap
    for section, options in conf.iteritems():
        bucket = configMap.setdefault(section, {})
        for key, value in options.iteritems():
            if override:
                bucket[key] = value
            else:
                bucket.setdefault(key, value)


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

