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
Main CherryPy module:
    - Parses config file
    - Creates the HTTP server
"""

import cpg, thread, _cputil, _cpconfig, _cphttpserver, time

def start(configFile = None, parsedConfigFile = None, configDict = {}, initOnly = 0):
    """
        Main function. All it does is this:
            - read/parse config file if any
            - create response and request objects
            - creates HTTP server based on configFile and configDict
            - start HTTP server

        Input: There are 2 ways to pass config options:
            - Let CherryPy parse a config file (configFile)
            - Pass the options as a dictionary (configDict)
    """

    # cpg.configOption contains an EmptyClass instance with all the configuration option
    _cpconfig.setDefaultConfigOption()

    # cpg.parsedConfigFile contains the ConfigParser instance with the parse config file
    cpg.parsedConfigFile = None

    if configFile:
        _cpconfig.parseConfigFile(configFile = configFile)
    elif parsedConfigFile:
        _cpconfig.parseConfigFile(parsedConfigFile = parsedConfigFile)

    if configDict:
        for key, value in configDict.items():
            setattr(cpg.configOption, key, value)

    # Output config options
    _cpconfig.outputConfigOptions()

    # Check the config options
    # TODO
    # _cpconfig.checkConfigOptions()

    # Create request and response object (the same objects will be used
    #   throughout the entire life of the webserver)
    cpg.request = _cputil.ThreadAwareClass()
    cpg.response = _cputil.ThreadAwareClass()
    # Create threadData object as a thread-specific all-purpose storage
    cpg.threadData = _cputil.ThreadAwareClass()

    # Initialize a few global variables
    cpg._lastCacheFlushTime = time.time()
    cpg._lastSessionCleanUpTime = time.time()
    cpg._sessionMap = {} # Map of "cookie" -> ("session object", "expiration time")

    if not initOnly:
        _cphttpserver.start()

def stop():
    _cphttpserver.stop()

# Set some special attributes for adding hooks
onStartServerList = []
onStartThreadList = []
onStopServerList = []
onStopThreadList = []
