"""
Copyright (c) 2004, CherryPy Team (team@cherrypy.org)
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
    * Neither the name of the CherryPy Team nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
import os,urllib,time,sys,signal,socket,httplib,os.path 

def startServer(infoMap):
    # Start the server in another thread
    if not hasattr(os, "fork"): # win32 mostly
        pid=os.spawnl(os.P_NOWAIT,infoMap['path'],infoMap['path'], '"'+os.path.join(os.getcwd(),'testsite.py')+'"')
    else:
        pid=os.fork()
        if not pid:
            os.execlp(infoMap['path'],infoMap['path'],'testsite.py')
    return pid

def getPage(url, cookies, extraRequestHeader = []):
    data=""
    i=0
    response = None
    class EmptyClass: pass
    cpg = EmptyClass()
    cpg.response = EmptyClass()
    cpg.response.body = None
    cpg.response.headerMap = {}
    while i<10:
        try:
            conn=httplib.HTTPConnection('127.0.0.1:8000')
            conn.putrequest("GET", url)
            conn.putheader("Host", "127.0.0.1")
            if cookies:
                cookieList = []
                for cookie in cookies:
                    i = cookie.find(' ')
                    j = cookie.find(';')
                    cookieList.append(cookie[i+1:j])
                cookieStr = '; '.join(cookieList)
                conn.putheader("Cookie", cookies[:j])

            for key, value in extraRequestHeader:
                conn.putheader(key, value)

            conn.endheaders()

            response=conn.getresponse()

            cookies=response.msg.getallmatchingheaders("Set-Cookie")

            cpg=EmptyClass()
            cpg.response = EmptyClass()
            cpg.response.headerMap = {'Status': response.status}
            for line in response.msg.headers:
                line = line.strip()
                i = line.find(':')
                key, value = line[:i], line[i+1:].strip()
                cpg.response.headerMap[key] = value

            cpg.response.body = response.read()

            conn.close()
            break
        except socket.error:
            time.sleep(0.5)
        i+=1
    return cpg, cookies

def shutdownServer(pid, mode):
    if mode=='t':
        u=urllib.urlopen("http://127.0.0.1:8000/shutdown/thread")
        try: u=urllib.urlopen("http://127.0.0.1:8000/shutdown/dummy")
        except IOError: pass
        except AttributeError: pass # Happens on Mac OS X when run with Python-2.3
    elif mode=='tp':
        u=urllib.urlopen("http://127.0.0.1:8000/shutdown/thread")
        try: u=urllib.urlopen("http://127.0.0.1:8000/shutdown/dummy")
        except IOError: pass # Happens on Windows
    else:
        try:
            u=urllib.urlopen("http://127.0.0.1:8000/shutdown/regular")
        except IOError: pass
        except AttributeError: pass # For Python2.3

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
* cpg.response.headerMap:
%s
* cpg.response.body:
%s""" % (rule, repr(cpg.response.headerMap), repr(cpg.response.body)))
        return False

def prepareCode(code):
    f = open('testsite.py', 'w')
    beforeStart = '''
class Shutdown:
    def dummy(self):
        return "OK"
    dummy.exposed = True
    def regular(self):
        import os
        os._exit(0)
    regular.exposed = True
    def thread(self):
        import threading
        for t in threading.enumerate(): t.setName("NOT RUNNING")
        return "OK"
    thread.exposed = True
cpg.root.shutdown = Shutdown()
def f(*a, **kw): return ""
cpg.root._cpLogMessage = f
'''
    includePathsToSysPath = """
import sys,os,os.path
sys.path.insert(0,os.path.normpath(os.path.join(os.getcwd(),'../../')))
"""
    f.write(includePathsToSysPath+code.replace('cpg.server.start', beforeStart + 'cpg.server.start'))
    f.close()

def checkPageResult(testName, infoMap, code, testList, failedList, extraConfig = '', extraRequestHeader = []):
    response = None
    prepareCode(code)
    # Try it in all 2 modes (regular, threadPooling)
    modeList=[('r',''), ('tp', 'threadPool=3')]
    for mode,modeConfig in modeList:
        f=open("testsite.cfg", "w")
        f.write(extraConfig)
        f.write('''
[session]
storageType=ram
[server]
socketPort = 8000
''')
        f.write(modeConfig)
        f.close()

        pid = startServer(infoMap)
        passed=True
        cookies=None
        for url, rule in testList:
            cpg, cookies = getPage(url, cookies, extraRequestHeader)
            if not checkResult(testName, infoMap, mode, cpg, rule, failedList):
                passed=0
                print "*** FAILED ***"
                break
        shutdownServer(pid, mode)
        if passed:
            print mode+"...",
            sys.stdout.flush()
        else: break
    if passed: print "passed"
    sys.stdout.flush()
    return response

