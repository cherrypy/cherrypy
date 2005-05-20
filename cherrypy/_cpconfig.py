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

class CaseSensitiveConfigParser(ConfigParser.ConfigParser):
    """ Sub-class of ConfigParser that keeps the case of options """
    def optionxform(self, optionstr):
        return optionstr

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
        
def loadConfigFile(configFile = None):
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
        if section not in cpg.configMap:
            cpg.configMap[section] = {}
        for option in configParser.options(section):
            # Check if we need to cast options
            funcName = cast.get(section, {}).get(option, 'get')
            value = getattr(configParser, funcName)(section, option)
            cpg.configMap[section][option] = value

def outputConfigMap():
    _cpLogMessage = _cputil.getSpecialFunction('_cpLogMessage')
    _cpLogMessage("Server parameters:", 'CONFIG')
    _cpLogMessage("  server.logToScreen: %s" % cpg.getConfig('server', 'logToScreen'), 'CONFIG')
    _cpLogMessage("  server.logFile: %s" % cpg.getConfig('server', 'logFile'), 'CONFIG')
    _cpLogMessage("  server.protocolVersion: %s" % cpg.getConfig('server', 'protocolVersion'), 'CONFIG')
    _cpLogMessage("  server.socketHost: %s" % cpg.getConfig('server', 'socketHost'), 'CONFIG')
    _cpLogMessage("  server.socketPort: %s" % cpg.getConfig('server', 'socketPort'), 'CONFIG')
    _cpLogMessage("  server.socketFile: %s" % cpg.getConfig('server', 'socketFile'), 'CONFIG')
    _cpLogMessage("  server.reverseDNS: %s" % cpg.getConfig('server', 'reverseDNS'), 'CONFIG')
    _cpLogMessage("  server.socketQueueSize: %s" % cpg.getConfig('server', 'socketQueueSize'), 'CONFIG')
    _cpLogMessage("  server.threadPool: %s" % cpg.getConfig('server', 'threadPool'), 'CONFIG')
    _cpLogMessage("  session.storageType: %s" % cpg.getConfig('session', 'storageType'), 'CONFIG')
    if cpg.getConfig('session', 'storageType'):
        _cpLogMessage("  session.timeout: %s min" % cpg.getConfig('session', 'timeout'), 'CONFIG')
        _cpLogMessage("  session.cleanUpDelay: %s min" % cpg.getConfig('session', 'cleanUpDelay'), 'CONFIG')
        _cpLogMessage("  session.cookieName: %s" % cpg.getConfig('session', 'cookieName'), 'CONFIG')
        _cpLogMessage("  session.storageFileDir: %s" % cpg.getConfig('session', 'storageFileDir'), 'CONFIG')
    _cpLogMessage("  staticContent: %s" % cpg.getConfig('staticContent'), 'CONFIG')

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

