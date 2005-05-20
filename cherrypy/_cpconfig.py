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

import _cputil, ConfigParser, cpg

# Default config options
configMap = {
        'server': {
            'protocolVersion': 'HTTP/1.0',
            'logToScreen': True,
            'logFile': '',
            'socketHost': '',
            'socketPort': 8080,
            'socketFile': '',
            'reverseDNS': False,
            'socketQueueSize': 5,
            'protocolVersion': 'HTTP/1.0',
            'threadPool': 0,
            'environment': 'dev'},
        'session': {
            'storageType': 'ram',
            'timeout': 60,
            'cleanUpDelay': 60,
            'cookieName': 'CherryPySession',
            'storageFileDir': '',
        },
        'staticContent': {}
    }

def update(updateMap = None, file = None):
    if updateMap is not None:
        for section, valueMap in updateMap.items():
            if section not in configMap:
                configMap[section] = valueMap
            else:
                for key, value in valueMap.items():
                    configMap[section][key] = value
    if file is not None:
        _load(file)

def get(section, attrName = None, defaultValue = None):
    if attrName:
        return configMap.get(section, {}).get(attrName, defaultValue)
    else:
        return configMap.get(section, defaultValue)

def getForPath(attrNam, defaultValue = None):
    raise "TODO"

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

# Known options to cast:
cast = {
    'server': {
        'logToScreen': 'getboolean',
        'socketPort': 'getint',
        'reverseDNS': 'getboolean',
        'socketQueueSize': 'getint',
        'threadPool': 'getint'},
    'session': {
        'sessionTimeout': 'getint',
        'cleanUpDelay': 'getint',
    }
}
        
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
            # Check if we need to cast options
            funcName = cast.get(section, {}).get(option, 'get')
            value = getattr(configParser, funcName)(section, option)
            configMap[section][option] = value

def outputConfigMap():
    _cpLogMessage = _cputil.getSpecialFunction('_cpLogMessage')
    _cpLogMessage("Server parameters:", 'CONFIG')
    _cpLogMessage("  server.logToScreen: %s" % cpg.config.get('server', 'logToScreen'), 'CONFIG')
    _cpLogMessage("  server.logFile: %s" % cpg.config.get('server', 'logFile'), 'CONFIG')
    _cpLogMessage("  server.protocolVersion: %s" % cpg.config.get('server', 'protocolVersion'), 'CONFIG')
    _cpLogMessage("  server.socketHost: %s" % cpg.config.get('server', 'socketHost'), 'CONFIG')
    _cpLogMessage("  server.socketPort: %s" % cpg.config.get('server', 'socketPort'), 'CONFIG')
    _cpLogMessage("  server.socketFile: %s" % cpg.config.get('server', 'socketFile'), 'CONFIG')
    _cpLogMessage("  server.reverseDNS: %s" % cpg.config.get('server', 'reverseDNS'), 'CONFIG')
    _cpLogMessage("  server.socketQueueSize: %s" % cpg.config.get('server', 'socketQueueSize'), 'CONFIG')
    _cpLogMessage("  server.threadPool: %s" % cpg.config.get('server', 'threadPool'), 'CONFIG')
    _cpLogMessage("  session.storageType: %s" % cpg.config.get('session', 'storageType'), 'CONFIG')
    if cpg.config.get('session', 'storageType'):
        _cpLogMessage("  session.timeout: %s min" % cpg.config.get('session', 'timeout'), 'CONFIG')
        _cpLogMessage("  session.cleanUpDelay: %s min" % cpg.config.get('session', 'cleanUpDelay'), 'CONFIG')
        _cpLogMessage("  session.cookieName: %s" % cpg.config.get('session', 'cookieName'), 'CONFIG')
        _cpLogMessage("  session.storageFileDir: %s" % cpg.config.get('session', 'storageFileDir'), 'CONFIG')
    _cpLogMessage("  staticContent: %s" % cpg.config.get('staticContent'), 'CONFIG')

def dummy():
    # Check that parameters are correct and that they don't conflict with each other
    if _protocolVersion not in ("HTTP/1.1", "HTTP/1.0"):
        raise "CherryError: protocolVersion must be 'HTTP/1.1' or 'HTTP/1.0'"
    if _reverseDNS not in (0,1): raise "CherryError: reverseDNS must be '0' or '1'"
    if _socketFile and not hasattr(socket, 'AF_UNIX'): raise "CherryError: Configuration file has socketFile, but this is only available on Unix machines"
    if _sslKeyFile:
        try:
            global SSL
            from OpenSSL import SSL
        except: raise "CherryError: PyOpenSSL 0.5.1 or later must be installed to use SSL. You can get it from http://pyopenssl.sourceforge.net"
    if _socketPort and _socketFile: raise "CherryError: In configuration file: socketPort and socketFile conflict with each other"
    if not _socketFile and not _socketPort: _socketPort=8000 # Default port
    if _sslKeyFile and not _sslCertificateFile: raise "CherryError: Configuration file has sslKeyFile but no sslCertificateFile"
    if _sslCertificateFile and not _sslKeyFile: raise "CherryError: Configuration file has sslCertificateFile but no sslKeyFile"
    try: sys.stdout.flush()
    except: pass

    if _sessionStorageType not in ('', 'custom', 'ram', 'file', 'cookie'): raise "CherryError: Configuration file an invalid sessionStorageType: '%s'"%_sessionStorageType
    if _sessionStorageType in ('custom', 'ram', 'cookie') and _sessionStorageFileDir!='': raise "CherryError: Configuration file has sessionStorageType set to 'custom, 'ram' or 'cookie' but a sessionStorageFileDir is specified"
    if _sessionStorageType=='file' and _sessionStorageFileDir=='': raise "CherryError: Configuration file has sessionStorageType set to 'file' but no sessionStorageFileDir"

