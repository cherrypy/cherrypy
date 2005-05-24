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

import cpg, urllib, sys, time, traceback, types, StringIO, cgi, os
import mimetypes, sha, random, string, _cputil, cperror, Cookie, urlparse
from lib.filter import basefilter
import _cpdefaults

"""
Common Service Code for CherryPy
"""

mimetypes.types_map['.dwg']='image/x-dwg'
mimetypes.types_map['.ico']='image/x-icon'

weekdayname = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
monthname = [None, 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

class IndexRedirect(Exception): pass

def parseFirstLine(data):
    cpg.request.path = data.split()[1]
    cpg.request.queryString = ""
    cpg.request.browserUrl = cpg.request.path
    cpg.request.paramMap = {}
    cpg.request.paramList = [] # Only used for Xml-Rpc
    cpg.request.filenameMap = {}
    cpg.request.fileTypeMap = {}
    # From http://www.cherrypy.org/ticket/141/
    # find the queryString, or set it to "" if not found
    if "?" in cpg.request.path:
        cpg.request.path, cpg.request.queryString = cpg.request.path.split("?",1)
    else:
        cpg.request.path, cpg.request.queryString = cpg.request.path, ""
    
    # build a paramMap dictionary from queryString
    pm = cpg.request.paramMap = cgi.parse_qs(cpg.request.queryString, True)
    for key, val in pm.items():
        if len(val) == 1:
            pm[key] = val[0]

def cookHeaders(clientAddress, remoteHost, headers, requestLine):
    """Process the headers into the request.headerMap"""
    cpg.request.headerMap = {}
    cpg.request.requestLine = requestLine
    cpg.request.simpleCookie = Cookie.SimpleCookie()

    # Build headerMap
    for item in headers.items():
        # Warning: if there is more than one header entry for cookies (AFAIK, only Konqueror does that)
        # only the last one will remain in headerMap (but they will be correctly stored in request.simpleCookie)
        insertIntoHeaderMap(item[0],item[1])

    # Handle cookies differently because on Konqueror, multiple cookies come on different lines with the same key
    cookieList = headers.getallmatchingheaders('cookie')
    for cookie in cookieList:
        cpg.request.simpleCookie.load(cookie)

    cpg.request.remoteAddr = clientAddress
    cpg.request.remoteHost = remoteHost

    # Set peer_certificate (in SSL mode) so the web app can examinate the client certificate
    try: cpg.request.peerCertificate = self.request.get_peer_certificate()
    except: pass

    _cputil.getSpecialFunction('_cpLogMessage')("%s - %s" % (cpg.request.remoteAddr, requestLine[:-2]), "HTTP")


def parsePostData(rfile):
    # Read request body and put it in data
    len = int(cpg.request.headerMap.get("Content-Length","0"))
    if len: data = rfile.read(len)
    else: data=""

    # Put data in a StringIO so FieldStorage can read it
    newRfile = StringIO.StringIO(data)
    # Create a copy of headerMap with lowercase keys because
    #   FieldStorage doesn't work otherwise
    lowerHeaderMap = {}
    for key, value in cpg.request.headerMap.items():
        lowerHeaderMap[key.lower()] = value
    forms = cgi.FieldStorage(fp = newRfile, headers = lowerHeaderMap, environ = {'REQUEST_METHOD':'POST'}, keep_blank_values = 1)
    for key in forms.keys():
        # Check if it's a list or not
        valueList = forms[key]
        if type(valueList) == type([]):
            # It's a list of values
            cpg.request.paramMap[key] = []
            cpg.request.filenameMap[key] = []
            cpg.request.fileTypeMap[key] = []
            for item in valueList:
                cpg.request.paramMap[key].append(item.value)
                cpg.request.filenameMap[key].append(item.filename)
                cpg.request.fileTypeMap[key].append(item.type)
        else:
            # It's a single value
            # In case it's a file being uploaded, we save the filename in a map (user might need it)
            cpg.request.paramMap[key] = valueList.value
            cpg.request.filenameMap[key] = valueList.filename
            cpg.request.fileTypeMap[key] = valueList.type

def applyFilterList(methodName):
    filterList = _cpdefaults._cpDefaultInputFilterList + \
        _cputil.getSpecialFunction('_cpFilterList') + \
        _cpdefaults._cpDefaultOutputFilterList
    for filter in filterList:
        method = getattr(filter, methodName, None)
        if method:
            method()

def insertIntoHeaderMap(key,value):
    normalizedKey = '-'.join([s.capitalize() for s in key.split('-')])
    cpg.request.headerMap[normalizedKey] = value

def initRequest(clientAddress, remoteHost, requestLine, headers, rfile, wfile):
    parseFirstLine(requestLine)
    cookHeaders(clientAddress, remoteHost, headers, requestLine)

    cpg.request.base = "http://" + cpg.request.headerMap.get('Host', '')
    cpg.request.browserUrl = cpg.request.base + cpg.request.browserUrl
    cpg.request.isStatic = False
    cpg.request.parsePostData = True
    cpg.request.rfile = rfile

    # Change objectPath in filters to change the object that will get rendered
    cpg.request.objectPath = None 

    applyFilterList('setConfig')
    applyFilterList('afterRequestHeader')

    if cpg.request.method == 'POST' and cpg.request.parsePostData:
        parsePostData(rfile)

    applyFilterList('afterRequestBody')

def doRequest(clientAddress, remoteHost, requestLine, headers, rfile, wfile):
    # creates some attributes on cpg.response so filters can use them
    cpg.response.wfile = wfile
    cpg.response.sendResponse = True
    cpg.response.body = None

    # Prepare response variables
    now = time.time()
    year, month, day, hh, mm, ss, wd, y, z = time.gmtime(now)
    date = "%s, %02d %3s %4d %02d:%02d:%02d GMT" % (weekdayname[wd], day, monthname[month], year, hh, mm, ss)
    cpg.response.headerMap = {
        "protocolVersion": cpg.config.get('server.protocolVersion'),
        "Status": "200 OK",
        "Content-Type": "text/html",
        "Server": "CherryPy/" + cpg.__version__,
        "Date": date,
        "Set-Cookie": [],
        "Content-Length": 0
    }
    cpg.response.simpleCookie = Cookie.SimpleCookie()

    try:
        try:
            initRequest(clientAddress, remoteHost, requestLine, headers, rfile, wfile)
        except basefilter.RequestHandled:
            # request was already fully handled; it may be a cache hit
            return
        except:
            # exception raised in a filter.
            # we don't have a response body yet, so create an empty one
            cpg.response.body = []
            raise
        handleRequest(cpg.response.wfile)
    except:
        # TODO: in some cases exceptions and filters are conflicting; 
        # error reporting seems to be broken in some cases. This code is 
        # a helper to check it
        err = ""
        exc_info_1 = sys.exc_info()[1]
        if hasattr(exc_info_1, 'args') and len(exc_info_1.args) >= 1:
            err = exc_info_1.args[0]

        try:
            _cputil.getSpecialFunction('_cpOnError')()

            # Still save session data
            if cpg.config.get('session.storageType') and not cpg.request.isStatic:
                sessionId = cpg.response.simpleCookie[cpg.config.get('session.cookieName')].value
                expirationTime = time.time() + cpg.config.get('session.timeout') * 60
                _cputil.getSpecialFunction('_cpSaveSessionData')(sessionId, cpg.request.sessionMap, expirationTime)

            applyFilterList('beforeErrorResponse')
            wfile.write('%s %s\r\n' % (cpg.response.headerMap['protocolVersion'], cpg.response.headerMap['Status']))

            if (cpg.response.headerMap.has_key('Content-Length') and
                    cpg.response.headerMap['Content-Length']==0):
                buf = StringIO.StringIO()
                [buf.write(x) for x in cpg.response.body]
                buf.seek(0)
                cpg.response.body = [buf.read()]
                cpg.response.headerMap['Content-Length'] = len(cpg.response.body[0])

            for key, valueList in cpg.response.headerMap.items():
                if key not in ('Status', 'protocolVersion'):
                    if type(valueList) != type([]): valueList = [valueList]
                    for value in valueList:
                        wfile.write('%s: %s\r\n'%(key, value))
            wfile.write('\r\n')
            for line in cpg.response.body:
                wfile.write(line)
            applyFilterList('afterErrorResponse')
        except:
            bodyFile = StringIO.StringIO()
            traceback.print_exc(file = bodyFile)
            body = bodyFile.getvalue()
            wfile.write('%s 200 OK\r\n' % cpg.config.get('server.protocolVersion'))
            wfile.write('Content-Type: text/plain\r\n')
            wfile.write('Content-Length: %s\r\n' % len(body))
            wfile.write('\r\n')
            wfile.write(body)

def sendResponse(wfile):
    applyFilterList('beforeResponse')

    # Set the content-length
    if (cpg.response.headerMap.has_key('Content-Length') and
            cpg.response.headerMap['Content-Length']==0):
        buf = StringIO.StringIO()
        [buf.write(x) for x in cpg.response.body]
        buf.seek(0)
        cpg.response.body = [buf.read()]
        cpg.response.headerMap['Content-Length'] = len(cpg.response.body[0])

    # Save session data
    if cpg.config.get('session.storageType') and not cpg.request.isStatic:
        sessionId = cpg.response.simpleCookie[cpg.config.get('session.cookieName')].value
        expirationTime = time.time() + cpg.config.get('session.timeout', cast='float') * 60
        _cputil.getSpecialFunction('_cpSaveSessionData')(sessionId, cpg.request.sessionMap, expirationTime)

    wfile.write('%s %s\r\n' % (cpg.response.headerMap['protocolVersion'], cpg.response.headerMap['Status']))
    for key, valueList in cpg.response.headerMap.items():
        if key not in ('Status', 'protocolVersion'):
            if type(valueList) != type([]): valueList = [valueList]
            for value in valueList:
                wfile.write('%s: %s\r\n' % (key, value))

    # Send response cookies
    cookie = cpg.response.simpleCookie.output()
    if cookie:
        wfile.write(cookie+'\r\n')
    wfile.write('\r\n')

    for line in cpg.response.body:
        wfile.write(line)
    
    # finalization hook for filter cleanup & logging purposes
    applyFilterList('afterResponse')

def handleRequest(wfile):
    # Clean up expired sessions if needed:
    now = time.time()
    if (cpg.config.get('session.storageType') and 
        cpg.config.get('session.cleanUpDelay', cast='float') and 
        (cpg._lastSessionCleanUpTime + cpg.config.get('session.cleanUpDelay', cast='float') * 60) <= now):
        cpg._lastSessionCleanUpTime = now
        _cputil.getSpecialFunction('_cpCleanUpOldSessions')()

    # Save original values (in case they get modified by filters)
    cpg.request.originalPath = cpg.request.path
    cpg.request.originalParamMap = cpg.request.paramMap
    cpg.request.originalParamList = cpg.request.paramList

    path = cpg.request.path
    if path.startswith('/'):
        # Remove leading slash
        path = path[1:]
    if path.endswith('/'):
        # Remove trailing slash
        path = path[:-1]
    path = urllib.unquote(path) # Replace quoted chars (eg %20) from url

    # Get session data
    if cpg.config.get('session.storageType') and not cpg.request.isStatic:
        now = time.time()
        # First, get sessionId from cookie
        try: sessionId = cpg.request.simpleCookie[cpg.config.get('session.cookieName')].value
        except: sessionId=None
        if sessionId:
            # Load session data from wherever it was stored
            sessionData = _cputil.getSpecialFunction('_cpLoadSessionData')(sessionId)
            if sessionData == None:
                sessionId = None
            else:
                cpg.request.sessionMap, expirationTime = sessionData
                # Check that is hasn't expired
                if now > expirationTime:
                    # Session expired
                    sessionId = None

        # Create a new sessionId if needed
        if not sessionId:
            cpg.request.sessionMap = {}
            sessionId = generateSessionId()
            cpg.request.sessionMap['_sessionId'] = sessionId

        cpg.response.simpleCookie[cpg.config.get('session.cookieName')] = sessionId
        cpg.response.simpleCookie[cpg.config.get('session.cookieName')]['path'] = '/'
        cpg.response.simpleCookie[cpg.config.get('session.cookieName')]['version'] = 1

    if cpg.response.body is None:
        try:
            func, objectPathList, virtualPathList = mapPathToObject()
        except IndexRedirect, inst:
            # For an IndexRedirect, we don't go through the regular
            #   mechanism: we return the redirect immediately
            newUrl = urlparse.urljoin(cpg.request.base, inst.args[0])
            wfile.write('%s 302\r\n' % (cpg.response.headerMap['protocolVersion']))
            cpg.response.headerMap['Location'] = newUrl
            for key, valueList in cpg.response.headerMap.items():
                if key not in ('Status', 'protocolVersion'):
                    if type(valueList) != type([]): valueList = [valueList]
                    for value in valueList:
                        wfile.write('%s: %s\r\n'%(key, value))
            wfile.write('\r\n')
            return
             
        # Remove "root" from objectPathList and join it to get objectPath
        cpg.request.objectPath = '/' + '/'.join(objectPathList[1:])
        body = func(*(virtualPathList + cpg.request.paramList), **(cpg.request.paramMap))
    else:
        body = cpg.response.body

    # builds a uniform return type
    if isinstance(body, types.FileType):
        cpg.response.body = fileGenerator(body)
    elif not isinstance(body, types.GeneratorType):
        cpg.response.body = [body]
    else:
        cpg.response.body = flattener(body)

    if cpg.response.sendResponse:
        sendResponse(wfile)

def fileGenerator(file, chunkSize = 65536): # 65536 = 64kb
   """ make file objects iterable generators """
   input = file.read(chunkSize)
   while input:
      yield input
      input = file.read(chunkSize) 


def flattener(input):
    for x in input:
        if not isinstance(x, types.GeneratorType):
            yield x
        else:
            for y in flattener(x):
                yield y 


def generateSessionId():
    s = ''
    for i in range(50):
        s += random.choice(string.letters+string.digits)
    s += '%s'%time.time()
    return sha.sha(s).hexdigest()

def getObjFromPath(objPathList):
    """ For a given objectPathList (like ['root', 'a', 'b', 'index']),
         return the object (or None if it doesn't exist).
    """
    root = cpg
    for objname in objPathList:
        # maps virtual filenames to Python identifiers (substitutes '.' for '_')
        objname = objname.replace('.', '_')
        root = getattr(root, objname, None)
        if root is None:
            return None

    return root


def mapPathToObject(path = None):
    # Traverse path:
    # for /a/b?arg=val, we'll try:
    #   root.a.b.index -> redirect to /a/b/?arg=val
    #   root.a.b.default(arg='val') -> redirect to /a/b/?arg=val
    #   root.a.b(arg='val')
    #   root.a.default('b', arg='val')
    #   root.default('a', 'b', arg='val')

    # Also, we ignore trailing slashes
    # Also, a method has to have ".exposed = True" in order to be exposed

    if path is None:
        path = cpg.request.objectPath or cpg.request.path
    if path.startswith('/'):
        path = path[1:] # Remove leading slash
    if path.endswith('/'):
        path = path[:-1] # Remove trailing slash

    if not path:
        objectPathList = []
    else:
        objectPathList = path.split('/')
    objectPathList = ['root'] + objectPathList + ['index']

    # Try successive objects... (and also keep the remaining object list)
    objCache = {}
    isFirst = True
    isSecond = False
    isDefault = False
    foundIt = False
    virtualPathList = []
    while objectPathList:
        if isFirst or isSecond:
            # Only try this for a.b.index() or a.b()
            candidate = getObjFromPath(objectPathList)
            if callable(candidate) and getattr(candidate, 'exposed', False):
                foundIt = True
                break
        # Couldn't find the object: pop one from the list and try "default"
        lastObj = objectPathList.pop()
        if (not isFirst) or (not path):
            virtualPathList.insert(0, lastObj)
            objectPathList.append('default')
            candidate = getObjFromPath(objectPathList)
            if callable(candidate) and getattr(candidate, 'exposed', False):
                foundIt = True
                isDefault = True
                break
            objectPathList.pop() # Remove "default"
        if isSecond:
            isSecond = False
        if isFirst:
            isFirst = False
            isSecond = True

    # Check results of traversal
    if not foundIt:
        raise cperror.NotFound (path)# We didn't find anything

    if isFirst:
        # We found the extra ".index"
        # Check if the original path had a trailing slash (otherwise, do
        #   a redirect)
        if cpg.request.path[-1] != '/':
            newUrl = cpg.request.path + '/'
            if cpg.request.queryString: newUrl += cpg.request.queryString
            raise IndexRedirect(newUrl)

    return candidate, objectPathList, virtualPathList
