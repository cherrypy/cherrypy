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

# return codes for _before and _after aspect methods
STOP = 0
CONTINUE = 1

import warnings
warnings.warn("The Aspect module is deprecated. You can use filters instead",
      DeprecationWarning)

class Aspect(object):
    """
    Base class for aspects. Derive new aspect classes from this, then
    override one or both of _before and _after.
    """

    def __getattribute__(self, methodName):

        # find method specified by methodName
        try:
            method = object.__getattribute__(self, methodName)
        except:
            raise

        # if requested attribute is not a method, simply return it
        if not callable(method):
            return method

        # define wrapper function
        def _wrapper(*k, **kw):
            # call _before method
            status, value = object.__getattribute__(self, '_before')(methodName, method)
            if status == STOP:
                return value

            # call wrapped method and append results
            result = method(*k, **kw)
            if value:
                result = value + result

            # call _after method
            status, value =  object.__getattribute__(self, '_after')(methodName, method)
            if status == STOP:
                return value
            if value:
                result += value

            # done!
            return result

        # expose wrapper function if wrapped method is exposed
        if getattr(method, 'exposed', None):
            _wrapper.exposed = True

        # return wrapper function. It'll get called instead of the
        # requested method.
        return _wrapper


    def _before(self, methodName, method):
        return CONTINUE, None


    def _after(self, methodName, method):
        return CONTINUE, None
