
import ConfigParser

import _cputil, cperror
from lib import autoreload

cpg = None # delayed import
def init():
    global cpg
    if not cpg:
        import cpg
    reset()

def reset(useDefaults=True):
    configMap.clear()
    if useDefaults:
        configMap["global"] = defaultGlobal.copy()

# This configMap dict holds the settings metadata for all cpg objects.
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
    
    'sessionFilter.default.on': True,
    'sessionFilter.default.timeout': 60,
    'sessionFilter.default.cleanUpDelay': 60,
    'sessionFilter.default.storageType' : 'ram',
    'sessionFilter.default.cookieName': 'CherryPySession',
    'sessionFilter.default.storageFileDir': '.sessionFiles'
    }

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

def get(key, defaultValue=None, returnSection=False, startPath = None):
    # Look, ma, no Python function calls! Uber-fast.
    # start path lest you overload the starting search path (needed by getAll)
    if startPath:
        path = startPath
    else:
        try:
            path = cpg.request.path
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
        
import os.path

def getAll(key):
    """
    getAll will lookup the key in the current node and all of its parent nodes,
    it will return a dictionary paths of each node containing the key and its value

    This function is required by the session filter
    """
    path = get(key, None, returnSection = True)
    value = get(key)
    
    result = {}
    while value != None and path != '/':
        result[path]= value
        path = os.path.split(path)[0]
        value = get(key, None, returnSection = False, startPath = path)
        path  = get(key, None, returnSection = True, startPath = path)
    
    if path == '/' and value != None:
        result[path] = value
    
    return result

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
        cpg.log("Reading infos from configFile stream", 'CONFIG')
        configParser.readfp(configFile)
    else:
        cpg.log("Reading infos from configFile: %s" % configFile, 'CONFIG')
        configParser.read(configFile)

    # Load INI file into cpg.configMap
    for section in configParser.sections():
        if section not in configMap:
            configMap[section] = {}
        for option in configParser.options(section):
            value = configParser.get(section, option)
            try:
                value = _cputil.unrepr(value)
            except cperror.WrongUnreprValue, s:
                msg = ("section: %s, option: %s, value: %s" %
                       (repr(section), repr(option), repr(value)))
                raise cperror.WrongConfigValue, msg
            configMap[section][option] = value

def outputConfigMap():
    cpg.log("Server parameters:", 'CONFIG')
    cpg.log("  server.environment: %s" % get('server.environment'), 'CONFIG')
    cpg.log("  server.logToScreen: %s" % get('server.logToScreen'), 'CONFIG')
    cpg.log("  server.logFile: %s" % get('server.logFile'), 'CONFIG')
    cpg.log("  server.protocolVersion: %s" % get('server.protocolVersion'), 'CONFIG')
    cpg.log("  server.socketHost: %s" % get('server.socketHost'), 'CONFIG')
    cpg.log("  server.socketPort: %s" % get('server.socketPort'), 'CONFIG')
    cpg.log("  server.socketFile: %s" % get('server.socketFile'), 'CONFIG')
    cpg.log("  server.reverseDNS: %s" % get('server.reverseDNS'), 'CONFIG')
    cpg.log("  server.socketQueueSize: %s" % get('server.socketQueueSize'), 'CONFIG')
    cpg.log("  server.threadPool: %s" % get('server.threadPool'), 'CONFIG')
    cpg.log("  session.storageType: %s" % get('session.storageType'), 'CONFIG')
    if get('session.storageType'):
        cpg.log("  session.timeout: %s min" % get('session.timeout'), 'CONFIG')
        cpg.log("  session.cleanUpDelay: %s min" % get('session.cleanUpDelay'), 'CONFIG')
        cpg.log("  session.cookieName: %s" % get('session.cookieName'), 'CONFIG')
        cpg.log("  session.storageFileDir: %s" % get('session.storageFileDir'), 'CONFIG')
    cpg.log("  staticContent: %s" % get('staticContent'), 'CONFIG')
