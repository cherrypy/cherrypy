"""
Copyright (c) 2004, CherryPy Team (team@cherrypy.org)
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
    * Neither the name of the CherryPy Team nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
import os,urllib,time,sys,signal,socket,httplib

def startServer(infoMap):
    # Start the server in another thread
    if not hasattr(os, "fork"): # win32 mostly
        pid=os.spawnl(os.P_NOWAIT, infoMap['path'], infoMap['path'], 'testsite.py')
    else:
        pid=os.fork()
        if not pid:
            os.execlp(infoMap['path'],infoMap['path'],'testsite.py')
    return pid

def getPage(url, cookies, isSSL=0, extraRequestHeader = []):
    data=""
    i=0
    response = None
    while i<10:
        try:
            if isSSL:
                conn=httplib.HTTPSConnection('127.0.0.1:8000')
            else:
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

            data=response.read()

            conn.close()
            break
        except socket.error:
            time.sleep(0.5)
        i+=1
    return data, cookies, response

def getXmlrpc(url, func, isSSL=0):
    import xmlrpclib
    http="http"
    if isSSL: http+="s"
    if url: url='/'+url
    data=""
    i=0
    try:
        while i<10:
            try:
                testsvr=xmlrpclib.Server(http+"://127.0.0.1:8000"+url)
                data=eval("testsvr.%s"%func)
                break
            except socket.error:
                time.sleep(0.5)
            i+=1
    except xmlrpclib.Fault, msg:
        return msg
    return data


def shutdownServer(pid, mode, isSSL=0):
    if isSSL: h="https"
    else: h="http"
    if mode=='t':
        u=urllib.urlopen(h+"://127.0.0.1:8000/shutdown/thread")
        if hasattr(socket, 'sslerror'): sslError = socket.sslerror
        else: sslError = 'dummy'
        try: u=urllib.urlopen(h+"://127.0.0.1:8000/shutdown/dummy")
        except IOError: pass
        except sslError: pass
        except AttributeError: pass # Happens on Mac OS X when run with Python-2.3
    elif mode=='tp':
        try: sslError = socket.sslerror
        except: sslError = 'dummy'
        u=urllib.urlopen(h+"://127.0.0.1:8000/shutdown/thread")
        try: u=urllib.urlopen(h+"://127.0.0.1:8000/shutdown/dummy")
        except IOError: pass # Happens on Windows
        except sslError: pass # Happens on Windows for https requests
    else:
        try:
            u=urllib.urlopen(h+"://127.0.0.1:8000/shutdown/regular")
        except IOError: pass
        except AttributeError: pass # For Python2.3

def checkResult(testName, infoMap, serverMode, result, expectedResult, failedList, exactResult):
    if result == expectedResult or ((not exactResult) and expectedResult in result):
        return True
    else:
        failedList.append(testName+" for python%s"%infoMap['exactVersionShort']+" in "+serverMode+" mode failed: expected result was:\n%s, actual result was:\n%s"%(repr(expectedResult), repr(result)))
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
    f.write(code.replace('cpg.server.start', beforeStart + 'cpg.server.start'))
    f.close()

def checkPageResult(testName, infoMap, code, config, urlList, expectedResultList, failedList, exactResult=True, isSSL=0, extraRequestHeader=[], expectedHeaderList=[]):
    response = None
    prepareCode(code)
    # Try it in all 3 modes (regular, threading, threadPooling) (we're missing forking and process pooling)
    modeList=[('r',''), ('tp', 'threadPool=3')]
    # modeList=[('r','')] # TODO
    for mode,modeConfig in modeList:
        f=open("testsite.cfg", "w")
        f.write(config)
        f.write('''
[session]
storageType=ram
[server]
socketPort = 8000
''')
        f.write(config+"\n"+modeConfig)
        f.close()

        pid = startServer(infoMap)
        passed=True
        cookies=None
        for i in range(len(urlList)):
            url=urlList[i]
            expectedResult=expectedResultList[i]
            result, cookies, response=getPage(url, cookies, isSSL, extraRequestHeader)
            if expectedHeaderList:
                if response.status != expectedHeaderList[0]:
                    failedList.append(testName+" for python%s"%infoMap['exactVersionShort']+" in "+mode+" mode failed: expected result status was %s, result status was %s"%(expectedHeaderList[0], response.status))
                    passed=0
                    print "*** FAILED ***"
                    break
            if not checkResult(testName, infoMap, mode, result, expectedResult, failedList, exactResult):
                passed=0
                print "*** FAILED ***"
                break
        shutdownServer(pid, mode, isSSL)
        if passed:
            print mode+"...",
            sys.stdout.flush()
        else: break
    if passed: print "passed"
    sys.stdout.flush()
    return response

