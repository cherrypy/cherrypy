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
import os,urllib,time,sys,signal,socket,httplib,os.path 

def startServer(infoMap):
    # Start the server in another thread
    if not hasattr(os, "fork"): # win32 mostly
        pid = os.spawnl(os.P_NOWAIT, infoMap['path'], infoMap['path'],
                        '"' + os.path.join(os.getcwd(), 'testsite.py') + '"')
    else:
        pid = os.fork()
        if not pid:
            os.execlp(infoMap['path'], infoMap['path'], 'testsite.py')
    return pid

class EmptyClass:
    pass

def getPage(url, cookies, extraRequestHeader = []):
    # The trying 10 times is simply in case of socket errors.
    # Normal case--it should run once.
    trial = 0
    while trial < 10:
        try:
            conn = httplib.HTTPConnection('127.0.0.1:%s' % PORT)
##            conn.set_debuglevel(1)
            conn.putrequest("GET", url)
##            conn.putheader("Host", "127.0.0.1")
            
            if cookies:
                for cookie in cookies:
                    name, value = cookie.split(":", 1)
                    conn.putheader("Cookie", value.strip())
            
            for key, value in extraRequestHeader:
                conn.putheader(key, value)
            
            conn.endheaders()
            
            response = conn.getresponse()
            
            cookies = response.msg.getallmatchingheaders("Set-Cookie")
            
            cpg = EmptyClass()
            cpg.response = EmptyClass()
            cpg.response.headerMap = {}
            cpg.response.status = "%s %s" % (response.status, response.reason)
            for line in response.msg.headers:
                key, value = line.split(":", 1)
                cpg.response.headerMap[key.strip()] = value.strip()
            
            cpg.response.body = response.read()
            
            conn.close()
            return cpg, cookies
        except socket.error:
            trial += 1
            if trial == 10:
                raise
            else:
                time.sleep(0.5)

def shutdownServer(mode):
    urllib.urlopen("http://127.0.0.1:%s/shutdown/all" % PORT)
    if mode.startswith('tp'):
        # In thread-pool mode, it can take up to 1 sec for the server
        #   to shutdown
        time.sleep(1.1)
    return

def checkResult(testName, infoMap, serverMode, cpg, rule, failedList):
    result = False
    try:
        result = eval(rule)
        if result:
            return result 
    except:
        pass 
    if not result:
        failedList.append(testName +
            " for python%s" % infoMap['exactVersionShort'] + 
            " in " + serverMode + " mode failed." + """
* Rule:
%s
* cpg.response.status:
%s
* cpg.response.headerMap:
%s
* cpg.response.body:
%s""" % (rule, repr(cpg.response.status),
         repr(cpg.response.headerMap), repr(cpg.response.body)))
        return False

def prepareCode(code, serverClass):
    f = open('testsite.py', 'w')
    
    includePathsToSysPath = """
import sys,os,os.path
sys.path.insert(0,os.path.normpath(os.path.join(os.getcwd(),'../../')))
"""
    f.write(includePathsToSysPath)
    
    beforeStart = '''
class Shutdown:
    def all(self):
        cpg.server.stop()
        return "Shut down"
    all.exposed = True
cpg.root.shutdown = Shutdown()
def f(*a, **kw): return ""
cpg.root._cpLogMessage = f
cpg.config.update(file = 'testsite.cfg')
'''
    newcode = code.replace('cpg.config.update', beforeStart + 'cpg.config.update')
    if serverClass:
        serverClass = "serverClass='%s'" % serverClass
    newcode = newcode.replace('cpg.server.start(',
                              'cpg.config.configMap["/"]["server.logToScreen"] = False\n'
                              'cpg.server.start(' + serverClass)
    f.write(newcode)
    
    f.close()

PORT = 8000
def port_is_free():
    try:
        s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('127.0.0.1', PORT))
        s.close()
        return False
    except socket.error:
        return True

def checkPageResult(testName, infoMap, code, testList, failedList, extraConfig = '', extraRequestHeader = []):
    response = None
    
    if not port_is_free():
        print "\n### Error: port", PORT, "is busy. The previous server did not shut down properly."
        sys.exit(-1)
    
    # Try it in all 4 modes (regular, threadPooling x normal, WSGI)
    for name, serverClass in [("native", "cherrypy._cphttpserver.embedded_server"),
                              ("wsgi", ""),
                              ]:
        sys.stdout.write(name + ": ")
        prepareCode(code, serverClass)
        for mode, modeConfig in [('r', ""), ('tp', 'server.threadPool = 3')]:
            sys.stdout.write(mode)
            sys.stdout.flush()
            f = open("testsite.cfg", "w")
            f.write(extraConfig)
            f.write('''
[/]
session.storageType = "ram"
server.socketPort = %s
server.environment = "production"
server.logToScreen = False
''' % PORT)
            f.write(modeConfig + "\n")
            f.close()
            
            pid = startServer(infoMap)
            passed=True
            cookies=None
            for url, rule in testList:
                sys.stdout.write(".")
                sys.stdout.flush()
                cpg, cookies = getPage(url, cookies, extraRequestHeader)
                if not checkResult(testName, infoMap, mode, cpg, rule, failedList):
                    passed = 0
                    print "*** FAILED ***",
                    break
            shutdownServer(mode)
            if passed:
                sys.stdout.write("ok ")
                sys.stdout.flush()
            if not passed:
                break
    if passed:
        print "passed"
    sys.stdout.flush()
    return response

