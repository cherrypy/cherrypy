import _cputil, cperror
import ConfigParser
from lib import autoreload

cpg = None # delayed import

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
    }
configMap = {"/": defaultGlobal.copy()}

def update(updateMap=None, file=None):
    if updateMap:
        for section, valueMap in updateMap.items():
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
    global cpg
    if not cpg:
        import cpg
    
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
            if path != "/":
                i = path.rfind("/")
                if i < 0:
                    result = defaultValue
                else:
                    path = path[:i]
                    continue
            else:
                result = defaultValue
        break
    
    if returnSection:
        return path
    else:
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
    _cpLogMessage = _cputil.getSpecialFunction('_cpLogMessage')

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
    _cpLogMessage = _cputil.getSpecialFunction('_cpLogMessage')
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
