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

import os, sys,os

def buildInfoMap(python2):
    print "Checking which python versions are installed..."
    for version, infoMap in python2.items():
        # Check if this version of python is installed:
        path=infoMap.get('path', sys.executable )
        if path:
            exactVersion=os.popen(
                '%s -c "import sys,os,os.path;' % path+
                """sys.path.insert(0,os.path.normpath(os.path.join(os.getcwd(),\'../../\')));"""+
                'import cherrypy;'+
                'print sys.version;'+
                'print cherrypy.__version__"').read().strip()
        if path and exactVersion and exactVersion.find('Traceback') == -1:
            exactVersionShort=exactVersion.split()[0]
            print "    Found python version %s with CherryPy version %s " % (exactVersionShort, exactVersion.split()[-1])
            python2[version]['exactVersion']=exactVersion
            python2[version]['exactVersionShort']=exactVersionShort
            python2[version]['path']=path
            if exactVersionShort.find("2.%s"%version)!=0:
                print
                print "*************************"
                print "Error: the path for python2.%s appears to run python%s"%(version, exactVersionShort)
                print 'By default, this script expects the python binaries to be in your PATH and to be called "python2.1", "python2.2", ...'
                print "If your setup is different, please edit this script and change the path for the python binary"
                sys.exit(-1)
        else:
            print "    Version 2.%s not found with cherrypy module, two directories up"%version
            del python2[version]

    if not python2:
        print
        print "*************************"
        print "Error: couldn't find any python distribution on your machine."
        print 'By default, this script expects the python binaries to be in your PATH and to be called "python2.1", "python2.2", ...'
        print "If your setup is different, please edit this script and change the path for the python binary"
        sys.exit(-1)
    print
    print "Finding out what modules are installed for these versions..."
    for version, infoMap in python2.items():
        print "    Checking modules for python%s..."%infoMap['exactVersionShort']

        # Test if python has fork
        res=os.popen('%s -c "import sys; sys.stderr=sys.stdout; import os; print hasattr(os,\'fork\')"'%infoMap['path']).read()
        if res.find('1')!=-1 or res.find('True')!=-1:
            print "        os.fork available"
            infoMap['hasFork']=1
        else:
            print "        os.fork not available"
            infoMap['hasFork']=0

        # Test if threads are available
        res=os.popen('%s -c "import sys; sys.stderr=sys.stdout; import thread"'%infoMap['path']).read()
        if res.find("ImportError")==-1:
            print "        thread available"
            infoMap['hasThread']=1
        else:
            print "        thread not available"
            infoMap['hasThread']=0

        # Test if pyOpenSSL is available
        res=os.popen('%s -c "import sys; sys.stderr=sys.stdout; from OpenSSL import SSL"'%infoMap['path']).read()
        if res.find("ImportError")==-1:
            print "        pyOpenSSL available"
            infoMap['hasPyOpenSSL']=1
        else:
            print "        pyOpenSSL not available"
            infoMap['hasPyOpenSSL']=0

        # Test if xmlrpclib is available
        res=os.popen('%s -c "import sys; sys.stderr=sys.stdout; import xmlrpclib"'%infoMap['path']).read()
        if res.find("ImportError")==-1:
            print "        xmlrpclib available"
            infoMap['hasXmlrpclib']=1
        else:
            print "        xmlrpclib not available"
            infoMap['hasXmlrpclib']=0

    return python2
