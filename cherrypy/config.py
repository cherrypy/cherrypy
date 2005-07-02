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

import os.path
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

    'sessionFilter.on' : False,
    'sessionFilter.sessionList' : ['default'],
    'sessionFIlter.storageAdaptors' : {},
    'sessionFilter.default.on': True,
    'sessionFilter.default.timeout': 60,
    'sessionFilter.default.cleanUpDelay': 60,
    'sessionFilter.default.storageType' : 'ram',
    'sessionFilter.default.cookiePrefix': 'CherryPySession',
    'sessionFilter.default.storagePath': '.sessiondata'
    }

def reset(useDefaults=True):
    configMap.clear()
    if useDefaults:
        configMap["global"] = defaultGlobal.copy()
reset()

def update(updateMap=None, file=None):
    if updateMap:
        for section, valueMap in updateMap.items():
            if not isinstance(valueMap, dict):
                # Shortcut syntax
                #   ex: update({'server.socketPort': 80})
                valueMap = {section: valueMap}
                section = 'global'
            s = configMap.get(section)
            if not s:
                configMap[section] = valueMap
            else:
                s.update(valueMap)
    if file:
        if file not in autoreload.reloadFiles:
            autoreload.reloadFiles.append(file)
        _load(file)

def get(key, defaultValue=None, returnSection=False):
    # Look, ma, no Python function calls! Uber-fast.

    try:
        path = cherrypy.request.path
    except AttributeError:
        path = "/"
    
    while True:
        if path == "":
            path = "/"
        try:
            result = configMap[path][key]
        except KeyError:
            if path not in ("/", "global"):
                i = path.rfind("/")
                if i < 0:
                    result = defaultValue
                else:
                    path = path[:i]
                    continue
            elif path != "global":
                path = "global"
                continue
            else:
                result = defaultValue
        break
    
    if returnSection:
        if path == 'global':
            return '/'
        return path
    else:
        return result

def getAll(key):
    """
    getAll will lookup the key in the current node and all of its parent nodes,
    it will return a list of path, value pairs
    This function is required by the session filter
    """
    
    try:
        path = cherrypy.request.path
    except AttributeError:
        path = "/"
    
    pathList = cherrypy.request.path.split('/')
    
    results = []
    
    try:
        results = [('/',  configMap['global'][key])]
    except KeyError:
        pass
    
    if path == '/':
        return results
    
    for n in xrange(1, len(pathList)):
        path = '/'.join(pathList[0:n+1])
        try:
            results.append(path, configMap[path][key])
        except KeyError:
            pass

    return results
       

class CaseSensitiveConfigParser(ConfigParser.ConfigParser):
    """ Sub-class of ConfigParser that keeps the case of options and
        that raises an exception if the file cannot be read
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
            self._read(fp, filename)
            fp.close()

def _load(configFile = None):
    """ Convert an INI file to a dictionary """
    
    # Parse config file
    configParser = CaseSensitiveConfigParser()
    if hasattr(configFile, 'read'):
        cherrypy.log("Reading infos from configFile stream", 'CONFIG')
        configParser.readfp(configFile)
    else:
        cherrypy.log("Reading infos from configFile: %s" % configFile, 'CONFIG')
        configParser.read(configFile)
    
    # Load INI file into cherrypy.configMap
    for section in configParser.sections():
        if section not in configMap:
            configMap[section] = {}
        for option in configParser.options(section):
            value = configParser.get(section, option)
            try:
                value = _cputil.unrepr(value)
            except _cperror.WrongUnreprValue, s:
                msg = ("section: %s, option: %s, value: %s" %
                       (repr(section), repr(option), repr(value)))
                raise _cperror.WrongConfigValue, msg
            configMap[section][option] = value

def outputConfigMap():
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
        cherrypy.log(  "  %s: %s" % (var, get(var)), 'CONFIG')

