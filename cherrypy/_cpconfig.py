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

        
def setDefaultConfigOption():
    """ Return an EmptyClass instance with the default config options """

    cpg.configOption = _cputil.EmptyClass()

    # Set default values for all options

    # Parameters used for logging
    cpg.configOption.logToScreen = 1
    cpg.configOption.logFile = ''

    # Parameters used to tell which socket the server should listen on
    # Note that socketPort and socketFile conflict wich each
    # other: if one has a non-null value, the other one should be null
    cpg.configOption.socketHost = ''
    cpg.configOption.socketPort = 8080
    cpg.configOption.socketFile = '' # Used if server should listen on
                                 # AF_UNIX socket
    cpg.configOption.reverseDNS = 0
    cpg.configOption.socketQueueSize = 5 # Size of the socket queue
    cpg.configOption.protocolVersion = "HTTP/1.0"

    # Parameters used to tell what kind of server we want
    # Note that numberOfProcesses, threading and forking conflict
    # wich each other: if one has a non-null value, the other
    # ones should be null (for numberOfProcesses, null means equal to one)
    cpg.configOption.processPool = 0 # Used if we want to fork n processes
                                 # at the beginning. In this case, all
                                 # processes will listen on the same
                                 # socket (this only works on unix)
    cpg.configOption.threading = 0 # Used if we want to create a new
                               # thread for each request
    cpg.configOption.forking = 0 # Used if we want to create a new process
                             # for each request
    cpg.configOption.threadPool = 0 # Used if we want to create a pool
                                # of threads at the beginning

    # Variables used to tell if this is an SSL server
    cpg.configOption.sslKeyFile = ""
    cpg.configOption.sslCertificateFile = ""
    cpg.configOption.sslClientCertificateVerification = 0
    cpg.configOption.sslCACertificateFile = ""
    cpg.configOption.sslVerifyDepth = 1

    # Variable used to flush cache
    cpg.configOption.flushCacheDelay=0

    # Variable used for enabling debugging
    cpg.configOption.debugMode=0

    # Variable used to serve static content
    cpg.configOption.staticContentList = []

    # Variable used for session handling
    cpg.configOption.sessionStorageType = ""
    cpg.configOption.sessionTimeout = 60 # In minutes
    cpg.configOption.sessionCleanUpDelay = 60 # In minutes
    cpg.configOption.sessionCookieName = "CherryPySession"
    cpg.configOption.sessionStorageFileDir = ""

def parseConfigFile(configFile = None, parsedConfigFile = None):
    """
        Parse the config file and set values in cpg.configOption
    """
    _cpLogMessage = _cputil.getSpecialFunction('_cpLogMessage')
    if configFile:
        cpg.parsedConfigFile = ConfigParser.ConfigParser()
        if hasattr(configFile, 'read'):
            _cpLogMessage("Reading infos from configFile stream", 'CONFIG')
            cpg.parsedConfigFile.readfp(configFile)
        else:
            _cpLogMessage("Reading infos from configFile: %s" % configFile, 'CONFIG')
            cpg.parsedConfigFile.read(configFile)
    else:
        cpg.parsedConfigFile = parsedConfigFile

    # Read parameters from configFile
    for sectionName, optionName, valueType in [
            ('server', 'logToScreen', 'int'),
            ('server', 'logFile', 'str'),
            ('server', 'socketHost', 'str'),
            ('server', 'protocolVersion', 'str'),
            ('server', 'socketPort', 'int'),
            ('server', 'socketFile', 'str'),
            ('server', 'reverseDNS', 'int'),
            ('server', 'processPool', 'int'),
            ('server', 'threadPool', 'int'),
            ('server', 'threading', 'int'),
            ('server', 'forking', 'int'),
            ('server', 'sslKeyFile', 'str'),
            ('server', 'sslCertificateFile', 'str'),
            ('server', 'sslClientCertificateVerification', 'int'),
            ('server', 'sslCACertificateFile', 'str'),
            ('server', 'sslVerifyDepth', 'int'),
            ('session', 'storageType', 'str'),
            ('session', 'timeout', 'float'),
            ('session', 'cleanUpDelay', 'float'),
            ('session', 'cookieName', 'str'),
            ('session', 'storageFileDir', 'str')
            ]:
        try:
            value = cpg.parsedConfigFile.get(sectionName, optionName)
            if valueType == 'int': value = int(value)
            elif valueType == 'float': value = float(value)
            if sectionName == 'session':
                optionName = 'session' + optionName[0].upper() + optionName[1:]
            setattr(cpg.configOption, optionName, value)
        except:
            pass

    try:
        staticDirList = cpg.parsedConfigFile.options('staticContent')
        for staticDir in staticDirList:
            staticDirTarget = cpg.parsedConfigFile.get('staticContent', staticDir)
            cpg.configOption.staticContentList.append((staticDir, staticDirTarget))
    except: pass

def outputConfigOptions():
    _cpLogMessage = _cputil.getSpecialFunction('_cpLogMessage')
    _cpLogMessage("Server parameters:", 'CONFIG')
    _cpLogMessage("  logToScreen: %s" % cpg.configOption.logToScreen, 'CONFIG')
    _cpLogMessage("  logFile: %s" % cpg.configOption.logFile, 'CONFIG')
    _cpLogMessage("  protocolVersion: %s" % cpg.configOption.protocolVersion, 'CONFIG')
    _cpLogMessage("  socketHost: %s" % cpg.configOption.socketHost, 'CONFIG')
    _cpLogMessage("  socketPort: %s" % cpg.configOption.socketPort, 'CONFIG')
    _cpLogMessage("  socketFile: %s" % cpg.configOption.socketFile, 'CONFIG')
    _cpLogMessage("  reverseDNS: %s" % cpg.configOption.reverseDNS, 'CONFIG')
    _cpLogMessage("  socketQueueSize: %s" % cpg.configOption.socketQueueSize, 'CONFIG')
    _cpLogMessage("  processPool: %s" % cpg.configOption.processPool, 'CONFIG')
    _cpLogMessage("  threadPool: %s" % cpg.configOption.threadPool, 'CONFIG')
    _cpLogMessage("  threading: %s" % cpg.configOption.threading, 'CONFIG')
    _cpLogMessage("  forking: %s" % cpg.configOption.forking, 'CONFIG')
    _cpLogMessage("  sslKeyFile: %s" % cpg.configOption.sslKeyFile, 'CONFIG')
    if cpg.configOption.sslKeyFile:
        _cpLogMessage("  sslCertificateFile: %s" % cpg.configOption.sslCertificateFile, 'CONFIG')
        _cpLogMessage("  sslClientCertificateVerification: %s" % cpg.configOption.sslClientCertificateVerification, 'CONFIG')
        _cpLogMessage("  sslCACertificateFile: %s" % cpg.configOption.sslCACertificateFile, 'CONFIG')
        _cpLogMessage("  sslVerifyDepth: %s" % cpg.configOption.sslVerifyDepth, 'CONFIG')
        _cpLogMessage("  flushCacheDelay: %s min" % cpg.configOption.flushCacheDelay, 'CONFIG')
    _cpLogMessage("  sessionStorageType: %s" % cpg.configOption.sessionStorageType, 'CONFIG')
    if cpg.configOption.sessionStorageType:
        _cpLogMessage("  sessionTimeout: %s min" % cpg.configOption.sessionTimeout, 'CONFIG')
        _cpLogMessage("  cleanUpDelay: %s min" % cpg.configOption.sessionCleanUpDelay, 'CONFIG')
        _cpLogMessage("  sessionCookieName: %s" % cpg.configOption.sessionCookieName, 'CONFIG')
        _cpLogMessage("  sessionStorageFileDir: %s" % cpg.configOption.sessionStorageFileDir, 'CONFIG')
    _cpLogMessage("  staticContent: %s" % cpg.configOption.staticContentList, 'CONFIG')

def dummy():
    # Check that parameters are correct and that they don't conflict with each other
    if _protocolVersion not in ("HTTP/1.1", "HTTP/1.0"):
        raise "CherryError: protocolVersion must be 'HTTP/1.1' or 'HTTP/1.0'"
    if _reverseDNS not in (0,1): raise "CherryError: reverseDNS must be '0' or '1'"
    if _socketFile and not hasattr(socket, 'AF_UNIX'): raise "CherryError: Configuration file has socketFile, but this is only available on Unix machines"
    if _processPool!=1 and not hasattr(os, 'fork'): raise "CherryError: Configuration file has processPool, but forking is not available on this operating system"
    if _forking and not hasattr(os, 'fork'): raise "CherryError: Configuration file has forking, but forking is not available on this operating system"
    if _sslKeyFile:
        try:
            global SSL
            from OpenSSL import SSL
        except: raise "CherryError: PyOpenSSL 0.5.1 or later must be installed to use SSL. You can get it from http://pyopenssl.sourceforge.net"
    if _socketPort and _socketFile: raise "CherryError: In configuration file: socketPort and socketFile conflict with each other"
    if not _socketFile and not _socketPort: _socketPort=8000 # Default port
    if _processPool==1: severalProcs=0
    else: severalProcs=1
    if _threadPool==1: severalThreads=0
    else: severalThreads=1
    if severalThreads+severalProcs+_threading+_forking>1: raise "CherryError: In configuration file: threadPool, processPool, threading and forking conflict with each other"
    if _sslKeyFile and not _sslCertificateFile: raise "CherryError: Configuration file has sslKeyFile but no sslCertificateFile"
    if _sslCertificateFile and not _sslKeyFile: raise "CherryError: Configuration file has sslCertificateFile but no sslKeyFile"
    try: sys.stdout.flush()
    except: pass

    if _sessionStorageType not in ('', 'custom', 'ram', 'file', 'cookie'): raise "CherryError: Configuration file an invalid sessionStorageType: '%s'"%_sessionStorageType
    if _sessionStorageType in ('custom', 'ram', 'cookie') and _sessionStorageFileDir!='': raise "CherryError: Configuration file has sessionStorageType set to 'custom, 'ram' or 'cookie' but a sessionStorageFileDir is specified"
    if _sessionStorageType=='file' and _sessionStorageFileDir=='': raise "CherryError: Configuration file has sessionStorageType set to 'file' but no sessionStorageFileDir"
    if _sessionStorageType=='ram' and (_forking or severalProcs):
        print "CherryWarning: 'ram' sessions might be buggy when using several processes"

