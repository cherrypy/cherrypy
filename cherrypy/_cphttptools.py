"""
Copyright (c) 2004, CherryPy Team (team@cherrypy.org)
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
    * Neither the name of the CherryPy Team nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import cpg, urllib, sys, time, traceback, types, StringIO, cgi, os
import mimetypes, sha, random, string, _cputil, cperror

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
    i = cpg.request.path.find('?')
    if i != -1:
        # Parse parameters from URL
        if cpg.request.path[i+1:]:
            k = cpg.request.path[i+1:].find('?')
            if k != -1:
                j = cpg.request.path[:k].rfind('=')
                if j != -1:
                    cpg.request.path = cpg.request.path[:j+1] + \
                        urllib.quote_plus(cpg.request.path[j+1:])
            for paramStr in cpg.request.path[i+1:].split('&'):
                sp = paramStr.split('=')
                if len(sp) > 2:
                    j = paramStr.find('=')
                    sp = (paramStr[:j], paramStr[j+1:])
                if len(sp) == 2:
                    key, value = sp
                    value = urllib.unquote_plus(value)
                    if cpg.request.paramMap.has_key(key):
                        # Already has a value: make a list out of it
                        if type(cpg.request.paramMap[key]) == type([]):
                            # Already is a list: append the new value to it
                            cpg.request.paramMap[key].append(value)
                        else:
                            # Only had one value so far: start a list
                            cpg.request.paramMap[key] = [cpg.request.paramMap[key], value]
                    else:
                        cpg.request.paramMap[key] = value
        cpg.request.queryString = cpg.request.path[i+1:]
        cpg.request.path = cpg.request.path[:i]

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
    filterList = _cputil.getSpecialFunction('_cpFilterList')
    for filter in filterList:
        method = getattr(filter, methodName, None)
        if method:
            method()

def insertIntoHeaderMap(key,value):
    normalizedKey = '-'.join([s.capitalize() for s in key.split('-')])
    cpg.request.headerMap[normalizedKey] = value

def doRequest(wfile):
    try:
        handleRequest(wfile)
    except:
        err = ""
        exc_info_1 = sys.exc_info()[1]
        if hasattr(exc_info_1, 'args') and len(exc_info_1.args) >= 1:
            err = exc_info_1.args[0]

        try:
            _cputil.getSpecialFunction('_cpOnError')()

            # Save session data
            if cpg.configOption.sessionStorageType and not cpg.request.isStatic:
                sessionId = cpg.response.simpleCookie[cpg.configOption.sessionCookieName].value
                expirationTime = time.time() + cpg.configOption.sessionTimeout * 60
                _cputil.getSpecialFunction('_cpSaveSessionData')(sessionId, cpg.request.sessionMap, expirationTime)

            wfile.write('%s %s\r\n' % (cpg.response.headerMap['protocolVersion'], cpg.response.headerMap['Status']))
            if cpg.response.headerMap.has_key('Content-Length') and cpg.response.headerMap['Content-Length'] == 0:
                cpg.response.headerMap['Content-Length'] = len(cpg.response.body)
            for key, valueList in cpg.response.headerMap.items():
                if key not in ('Status', 'protocolVersion'):
                    if type(valueList) != type([]): valueList = [valueList]
                    for value in valueList:
                        wfile.write('%s: %s\r\n'%(key, value))
            wfile.write('\r\n')
            wfile.write(cpg.response.body)
        except:
            bodyFile = StringIO.StringIO()
            traceback.print_exc(file = bodyFile)
            body = bodyFile.getvalue()
            wfile.write('%s 200 OK\r\n' % cpg.configOption.protocolVersion)
            wfile.write('Content-Type: text/plain\r\n')
            wfile.write('Content-Length: %s\r\n' % len(body))
            wfile.write('\r\n')
            wfile.write(body)

def sendResponse(wfile):
    applyFilterList('beforeResponse')

    # Save session data
    if cpg.configOption.sessionStorageType and not cpg.request.isStatic:
        sessionId = cpg.response.simpleCookie[cpg.configOption.sessionCookieName].value
        expirationTime = time.time() + cpg.configOption.sessionTimeout * 60
        _cputil.getSpecialFunction('_cpSaveSessionData')(sessionId, cpg.request.sessionMap, expirationTime)

    # Set the content-length
    if cpg.response.headerMap.has_key('Content-Length') and cpg.response.headerMap['Content-Length']==0:
        cpg.response.headerMap['Content-Length'] = len(cpg.response.body)

    wfile.write('%s %s\r\n' % (cpg.response.headerMap['protocolVersion'], cpg.response.headerMap['Status']))
    for key, valueList in cpg.response.headerMap.items():
        if key not in ('Status', 'protocolVersion'):
            if type(valueList) != type([]): valueList = [valueList]
            for value in valueList:
                wfile.write('%s: %s\r\n'%(key, value))

    # Send response cookies
    cookie = cpg.response.simpleCookie.output()
    if cookie:
        wfile.write(cookie+'\r\n')
    wfile.write('\r\n')

    applyFilterList('afterResponseHeader')

    applyFilterList('beforeResponseFullBody')

    # Check that the response body is a string
    if type(cpg.response.body) != types.StringType:
        raise cperror.WrongResponseType

    wfile.write(cpg.response.body)

def handleRequest(wfile):
    now = time.time()
    year, month, day, hh, mm, ss, wd, y, z = time.gmtime(now)
    date = "%s, %02d %3s %4d %02d:%02d:%02d GMT" % (weekdayname[wd], day, monthname[month], year, hh, mm, ss)
    cpg.response.headerMap={"Status": "200 OK", "protocolVersion": cpg.configOption.protocolVersion, "Content-Type": "text/html", "Server": "CherryPy/" + cpg.__version__, "Date": date, "Set-Cookie": [], "Content-Length": 0}

    # Two variables used for streaming
    cpg.response.wfile = wfile
    cpg.response.sendResponse = 1

    if cpg.configOption.sslKeyFile:
        cpg.request.base = "https://" + cpg.request.headerMap['Host']
    else:
        cpg.request.base = "http://" + cpg.request.headerMap['Host']
    cpg.request.browserUrl = cpg.request.base + cpg.request.browserUrl
    cpg.request.isStatic = 0

    # TODO: Temp hack ... These filters shouldn't be here and remi
    # needs to rewrite this code ...
    applyFilterList('afterRequestHeader')
    applyFilterList('afterRequestBody')

    # Clean up expired sessions if needed:
    if cpg.configOption.sessionStorageType and cpg.configOption.sessionCleanUpDelay and cpg._lastSessionCleanUpTime + cpg.configOption.sessionCleanUpDelay * 60 <= now:
        cpg._lastSessionCleanUpTime = now
        _cputil.getSpecialFunction('_cpCleanUpOldSessions')()

    # Save original values (in case they get modified by filters)
    cpg.request.originalPath = cpg.request.path
    cpg.request.originalParamMap = cpg.request.paramMap
    cpg.request.originalParamList = cpg.request.paramList

    path = cpg.request.path
    if path.startswith('/'): path = path[1:] # Remove leading slash
    if path.endswith('/'): path = path[:-1] # Remove trailing slash

    # Handle static directories
    for urlDir, fsDir in cpg.configOption.staticContentList:
        if path == urlDir or path[:len(urlDir)+1]==urlDir+'/':

            cpg.request.isStatic = 1

            fname = fsDir + path[len(urlDir):]
            try:
                stat = os.stat(fname)
            except OSError:
                raise cperror.NotFound
            if type(stat) == type(()): # Python2.1
                modifTime = stat[9]
            else:
                modifTime = stat.st_mtime

            strModifTime = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(modifTime))

            # Check if browser sent "if-modified-since" in request header
            if cpg.request.headerMap.has_key('If-Modified-Since'):
                # Check if if-modified-since date is the same as strModifTime
                if cpg.request.headerMap['If-Modified-Since'] == strModifTime:
                    cpg.response.headerMap = {'Status': 304, 'protocolVersion': cpg.configOption.protocolVersion, 'Date': date}
                    cpg.response.body = ''
                    sendResponse(wfile)
                    return

            cpg.response.headerMap['Last-Modified'] = strModifTime
            f=open(fname, 'rb')
            cpg.response.body = f.read()
            f.close()
            # Set content-type based on filename extension
            i = path.rfind('.')
            if i != -1: ext = path[i:]
            else: ext = ""
            contentType = mimetypes.types_map.get(ext, "text/plain")
            cpg.response.headerMap['Content-Type'] = contentType
            sendResponse(wfile)
            return

    # Get session data
    if cpg.configOption.sessionStorageType and not cpg.request.isStatic:
        now = time.time()
        # First, get sessionId from cookie
        try: sessionId = cpg.request.simpleCookie[cpg.configOption.sessionCookieName].value
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

        cpg.response.simpleCookie[cpg.configOption.sessionCookieName] = sessionId
        cpg.response.simpleCookie[cpg.configOption.sessionCookieName]['path'] = '/'
        cpg.response.simpleCookie[cpg.configOption.sessionCookieName]['version'] = 1

    try:
        func, objectPathList, virtualPathList = mapPathToObject()
    except IndexRedirect, inst:
        # For an IndexRedirect, we don't go through the regular
        #   mechanism: we return the redirect immediately
        newUrl = canonicalizeUrl(inst.args[0])
        wfile.write('%s 302\r\n' % (cpg.response.headerMap['protocolVersion']))
        cpg.response.headerMap['Location'] = newUrl
        for key, valueList in cpg.response.headerMap.items():
            if key not in ('Status', 'protocolVersion'):
                if type(valueList) != type([]): valueList = [valueList]
                for value in valueList:
                    wfile.write('%s: %s\r\n'%(key, value))
        wfile.write('\r\n')
        return
         
    cpg.request.objectPath = '/'.join(objectPathList)
    cpg.response.body = func(*(virtualPathList + cpg.request.paramList), **(cpg.request.paramMap))

    if cpg.response.sendResponse:
        sendResponse(wfile)

def generateSessionId():
    s = ''
    for i in range(50):
        s += random.choice(string.letters+string.digits)
    s += '%s'%time.time()
    return sha.sha(s).hexdigest()

def getObjFromPath(objPathList, objCache):
    """ For a given objectPathList (like ['root', 'a', 'b', 'index']),
         return the object (or None if it doesn't exist).
         Also keep a cache for maximum efficiency
    """
    # Let cpg be the first valid object.
    validObjects = ["cpg"]
     
    # Scan the objPathList in order from left to right
    for index, obj in enumerate(objPathList):
        # currentObjStr holds something like 'cpg.root.something.else'
        currentObjStr = ".".join(validObjects)

        #---------------
        #   Cache check
        #---------------
        # Generate a cacheKey from the first 'index' elements of objPathList
        cacheKey = tuple(objPathList[:index+1])
        # Is this cacheKey in the objCache?
        if cacheKey in objCache: 
            # And is its value not None?
            if objCache[cacheKey]:
                # Yes, then add it to the list of validObjects
                validObjects.append(obj)
                # OK, go to the next iteration
                continue
            # Its value is None, so we stop
            # (This means it is not a valid object)
            break
        
        #-----------------
        # Attribute check
        #-----------------
        if getattr(eval(currentObjStr), obj, None):
            #  obj is a valid attribute of the current object
            validObjects.append(obj)
            #  Store it in the cache
            objCache[cacheKey] = eval(".".join(validObjects))
        else:
            # obj is not a valid attribute
            # Store None in the cache
            objCache[cacheKey] = None
            # Stop, we won't process the remaining objPathList
            break

    # Return the last cached object (even if its None)
    return objCache[cacheKey]

def mapPathToObject():
    # Traverse path:
    # for /a/b?arg=val, we'll try:
    #   root.a.b.index -> redirect to /a/b/?arg=val
    #   root.a.b.default(arg='val') -> redirect to /a/b/?arg=val
    #   root.a.b(arg='val')
    #   root.a.default('b', arg='val')
    #   root.default('a', 'b', arg='val')

    # Also, we ignore trailing slashes
    # Also, a method has to have ".exposed = True" in order to be exposed

    path = cpg.request.path
    if path.startswith('/'): path = path[1:] # Remove leading slash
    if path.endswith('/'): path = path[:-1] # Remove trailing slash

    if not path:
        objectPathList = []
    else:
        objectPathList = path.split('/')
    objectPathList = ['root'] + objectPathList + ['index']

    # Try successive objects... (and also keep the remaining object list)
    objCache = {}
    isFirst = True
    isDefault = False
    foundIt = False
    virtualPathList = []
    while objectPathList:
        candidate = getObjFromPath(objectPathList, objCache)
        if callable(candidate) and getattr(candidate, 'exposed', False):
            foundIt = True
            break
        # Couldn't find the object: pop one from the list and try "default"
        lastObj = objectPathList.pop()
        if not isFirst:
            virtualPathList.insert(0, lastObj)
            objectPathList.append('default')
            candidate = getObjFromPath(objectPathList, objCache)
            if callable(candidate) and getattr(candidate, 'exposed', False):
                foundIt = True
                isDefault = True
                break
            objectPathList.pop() # Remove "default"
        isFirst = False

    # Check results of traversal
    if not foundIt:
        raise cperror.NotFound # We didn't find anything

    if isFirst:
        # We found the extra ".index"
        # Check if the original path had a trailing slash (otherwise, do
        #   a redirect)
        if cpg.request.path[-1] != '/':
            newUrl = cpg.request.path + '/'
            if cpg.request.queryString: newUrl += cpg.request.queryString
            raise IndexRedirect(newUrl)

    return candidate, objectPathList, virtualPathList
    
def canonicalizeUrl(newUrl):
    if not newUrl.startswith('http://') and not newUrl.startswith('https://'):
        # If newUrl is not canonical, we must make it canonical
        if newUrl[0] == '/':
            # URL was absolute: we just add the request.base in front of it
            newUrl = cpg.request.base + newUrl
        else:
            # URL was relative
            if cpg.request.browserUrl == cpg.request.base:
                # browserUrl is request.base
                newUrl = cpg.request.base + '/' + newUrl
            else:
                newUrl = cpg.request.browserUrl[:i+1] + newUrl
    return newUrl
