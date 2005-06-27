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
A module containing a few utility classes/functions used by CherryPy
"""

import sys
import traceback
import time
import cherrypy


class EmptyClass:
    """ An empty class """
    pass


def getObjectTrail():
    """ Return all objects from the currenct object to cherrypy """
    root = getattr(cherrypy, 'root', None)
    if root:
        objectTrail = [root]
        # Try object path
        try:
            path = cherrypy.request.objectPath or cherrypy.request.path
        except AttributeError:
            path = '/'
        if path:
            pathList = path.split('/')[1:]
            
            # Successively get objects from the path
            for newObj in pathList:
                try:
                    root = getattr(root, newObj)
                    objectTrail.append(root)
                except AttributeError:
                    break
        
        return objectTrail
    return None

def getSpecialAttribute(name):
    """Return the special attribute. A special attribute is one that
    applies to all of the children from where it is defined, such as
    _cpFilterList."""
    
    # First, we look in the right-most object if this special attribute is implemented.
    # If not, then we try the previous object and so on until we reach cherrypy.root
    # If it's still not there, we use the implementation from this module.
    
    objectList = getObjectTrail()
    if objectList:
        
        objectList.reverse()
        for obj in objectList:
            attr = getattr(obj, name, None)
            if attr != None:
                return attr
    
    try:
        return globals()[name]
    except KeyError:
        raise cherrypy.InternalError("Special attribute %s could not be found"
                                     % repr(name))

def getSpecialAttributePath(name):
    """ Return the path to the special attribute """
    objectList = getObjectTrail()
    if objectList:
        pathList = cherrypy.request.objectPath or cherrypy.request.path
        pathList = pathList.split("/")[1:]
        for i in xrange(len(objectList) - 1, -1, -1):
            if hasattr(objectList[i], name):
                return "/" + "/".join(pathList[:i] + [name])
    raise cherrypy.InternalError("Special attribute %s could not be found"
                                 % repr(name))

def _cpLogMessage(msg, context = '', severity = 0):
    """ Default method for logging messages """
    
    nowTuple = time.localtime(time.time())
    nowStr = '%04d/%02d/%02d %02d:%02d:%02d' % (nowTuple[:6])
    if severity == 0:
        level = "INFO"
    elif severity == 1:
        level = "WARNING"
    elif severity == 2:
        level = "ERROR"
    else:
        level = "UNKNOWN"
    try:
        logToScreen = cherrypy.config.get('server.logToScreen')
    except:
        logToScreen = True
    s = nowStr + ' ' + context + ' ' + level + ' ' + msg
    if logToScreen:
        print s
    if cherrypy.config.get('server.logFile'):
        f = open(cherrypy.config.get('server.logFile'), 'ab')
        f.write(s + '\n')
        f.close()


def formatExc(exc=None):
    """formatExc(exc=None) -> exc (or sys.exc_info), formatted."""
    if exc is None:
        exc = sys.exc_info()
    return "".join(traceback.format_exception(*exc))

def _cpOnError():
    """ Default _cpOnError method """
    cherrypy.response.body = [formatExc()]
    cherrypy.response.headerMap['Content-Type'] = 'text/plain'
    if cherrypy.response.headerMap.has_key('Content-Encoding'):
        del cherrypy.response.headerMap['Content-Encoding']


_cpFilterList = []

# Filters that are always included
from cherrypy.lib.filter import baseurlfilter, cachefilter, \
    decodingfilter, encodingfilter, gzipfilter, logdebuginfofilter, \
    staticfilter, nsgmlsfilter, tidyfilter, \
    virtualhostfilter, xmlrpcfilter, sessionauthenticatefilter

from cherrypy.lib.filter import sessionfilter

_cachefilter = cachefilter.CacheFilter()
_logdebuginfofilter = logdebuginfofilter.LogDebugInfoFilter()
_nsgmlsfilter = nsgmlsfilter.NsgmlsFilter()
_sessionfilter = sessionfilter.SessionFilter()
_tidyfilter = tidyfilter.TidyFilter()
_xmlfilter = xmlrpcfilter.XmlRpcFilter()

# These are in order for a reason!

_cpDefaultInputFilterList = [
    _cachefilter,
    _logdebuginfofilter,
    virtualhostfilter.VirtualHostFilter(),
    baseurlfilter.BaseUrlFilter(),
    decodingfilter.DecodingFilter(),
    _sessionfilter,
    sessionauthenticatefilter.SessionAuthenticateFilter(),
    staticfilter.StaticFilter(),
    _nsgmlsfilter,
    _tidyfilter,
    _xmlfilter,
]
_cpDefaultOutputFilterList = [
    _xmlfilter,
    encodingfilter.EncodingFilter(),
    _tidyfilter,
    _nsgmlsfilter,
    _logdebuginfofilter,
    gzipfilter.GzipFilter(),
    _sessionfilter,
    _cachefilter,
]

# public domain "unrepr" implementation, found on the web and then improved.
import compiler

def getObj(s):
    s = "a=" + s
    p = compiler.parse(s)
    return p.getChildren()[1].getChildren()[0].getChildren()[1]

class UnknownType(Exception):
    pass

class Builder:

    def build(self, o):
        m = getattr(self, 'build_'+o.__class__.__name__, None)
        if m is None:
            raise UnknownType(o.__class__.__name__)
        return m(o)

    def build_List(self, o):
        return map(self.build, o.getChildren())

    def build_Const(self, o):
        return o.value

    def build_Dict(self, o):
        d = {}
        i = iter(map(self.build, o.getChildren()))
        for el in i:
            d[el] = i.next()
        return d

    def build_Tuple(self, o):
        return tuple(self.build_List(o))

    def build_Name(self, o):
        if o.name == 'None':
            return None
        elif o.name == 'True':
            return True
        elif o.name == 'False':
            return False
        raise UnknownType(o.name)

    def build_Add(self, o):
        real, imag = map(self.build_Const, o.getChildren())
        try:
            real = float(real)
        except TypeError:
            raise UnknownType('Add')
        if not isinstance(imag, complex) or imag.real != 0.0:
            raise UnknownType('Add')
        return real+imag

def unrepr(s):
    if not s:
        return s
    try:
        return Builder().build(getObj(s))
    except:
        raise cherrypy.WrongUnreprValue, repr(s)
