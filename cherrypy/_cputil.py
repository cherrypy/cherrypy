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

import time, thread, cpg, _cpdefaults, cperror

try: import zlib
except ImportError: pass

class EmptyClass:
    """ An empty class """
    pass

def getSpecialFunction(name):
    """ Return the special function """

    # First, we look in the right-most object if this special function is implemented.
    # If not, then we try the previous object and so on until we reach cpg.root
    # If it's still not there, we use the implementation from the
    # "_cpdefaults.py" module
    

    moduleList = [_cpdefaults]
    root = getattr(cpg, 'root', None)
    if root:
        moduleList.append(root)
        # Try object path
        try:
            path = cpg.request.objectPath or cpg.request.path
        except:
            path = '/'
        if path:
            pathList = path.split('/')[1:]

            obj = cpg.root
            previousObj = None
            # Successively get objects from the path
            for newObj in pathList:
                previousObj = obj
                try:
                    obj = getattr(obj, newObj)
                    moduleList.append(obj)
                except AttributeError:
                    break

    moduleList.reverse()
    for module in moduleList:
        func = getattr(module, name, None)
        if func != None:
            return func

    raise cperror.InternalError, "Special function %s could not be found" % repr(name)

