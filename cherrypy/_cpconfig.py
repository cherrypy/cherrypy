
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

    'session.storageType': 'ram',
    'session.timeout': 60,
    'session.cleanUpDelay': 60,
    'session.cookieName': 'CherryPySession',
    'session.storageFileDir': '',
    
    'sessionFilter.on': False,
    'sessionFilter.timeout': 60,
    'sessionFilter.cleanUpDelay': 60,
    'sessionFilter.storageType' : 'ram',
    'sessionFilter.cookieName': 'CherryPySession',
    'sessionFilter.storageFileDir': '.sessionFiles',
    
    'sessionFilter.new': 'sessionMap', # legacy setting
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
    _cpLogMessage = _cputil.getSpecialAttribute('_cpLogMessage')

    # Parse config file
    configParser = CaseSensitiveConfigParser()
    if hasattr(configFile, 'read'):
        _cpLogMessage("Reading infos from configFile stream", 'CONFIG')
        configParser.readfp(configFile)
    else:
        _cpLogMessage("Reading infos from configFile: %s" % configFile, 'CONFIG')
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
    _cpLogMessage = _cputil.getSpecialAttribute('_cpLogMessage')
    _cpLogMessage("Server parameters:", 'CONFIG')
    _cpLogMessage("  server.environment: %s" % get('server.environment'), 'CONFIG')
    _cpLogMessage("  server.logToScreen: %s" % get('server.logToScreen'), 'CONFIG')
    _cpLogMessage("  server.logFile: %s" % get('server.logFile'), 'CONFIG')
    _cpLogMessage("  server.protocolVersion: %s" % get('server.protocolVersion'), 'CONFIG')
    _cpLogMessage("  server.socketHost: %s" % get('server.socketHost'), 'CONFIG')
    _cpLogMessage("  server.socketPort: %s" % get('server.socketPort'), 'CONFIG')
    _cpLogMessage("  server.socketFile: %s" % get('server.socketFile'), 'CONFIG')
    _cpLogMessage("  server.reverseDNS: %s" % get('server.reverseDNS'), 'CONFIG')
    _cpLogMessage("  server.socketQueueSize: %s" % get('server.socketQueueSize'), 'CONFIG')
    _cpLogMessage("  server.threadPool: %s" % get('server.threadPool'), 'CONFIG')
    _cpLogMessage("  session.storageType: %s" % get('session.storageType'), 'CONFIG')
    if get('session.storageType'):
        _cpLogMessage("  session.timeout: %s min" % get('session.timeout'), 'CONFIG')
        _cpLogMessage("  session.cleanUpDelay: %s min" % get('session.cleanUpDelay'), 'CONFIG')
        _cpLogMessage("  session.cookieName: %s" % get('session.cookieName'), 'CONFIG')
        _cpLogMessage("  session.storageFileDir: %s" % get('session.storageFileDir'), 'CONFIG')
    _cpLogMessage("  staticContent: %s" % get('staticContent'), 'CONFIG')
