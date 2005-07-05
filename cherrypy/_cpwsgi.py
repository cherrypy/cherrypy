"""
Copyright (c) 2005, CherryPy Team (team@cherrypy.org)
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
A WSGI application and server (see PEP 333).
"""

import sys
import cherrypy
from cherrypy import _cputil, _cphttptools, _cpwsgiserver


def requestLine(environ):
    # Rebuild first line of the request
    resource = environ.get('SCRIPT_NAME', '') + environ.get('PATH_INFO', '')
    if not resource.startswith("/"):
        resource = "/" + resource
    qString = environ.get('QUERY_STRING')
    if qString:
        resource += '?' + qString
    return ('%s %s %s' % (environ['REQUEST_METHOD'],
                          resource or '/',
                          environ['SERVER_PROTOCOL']
                          )
            )

headerNames = {'HTTP_CGI_AUTHORIZATION': 'Authorization',
               'CONTENT_LENGTH': 'Content-Length',
               'CONTENT_TYPE': 'Content-Type',
               'REMOTE_HOST': 'Remote-Host',
               'REMOTE_ADDR': 'Remote-Addr',
               }

def translate_headers(environ):
    for cgiName in environ:
        translatedHeader = headerNames.get(cgiName.upper())
        if translatedHeader:
            yield translatedHeader, environ[cgiName]
        elif cgiName.upper().startswith("HTTP_"):
            # Hackish attempt at recovering original header names.
            translatedHeader = cgiName[5:].replace("_", "-")
            yield translatedHeader, environ[cgiName]


class NullWriter(object):
    
    def write(self, data):
        pass


def wsgiApp(environ, start_response):
    
    # Trap screen output from BaseHTTPRequestHandler.log_message()
    if not cherrypy.config.get('server.logToScreen'):
        sys.stderr = NullWriter()
    
    try:
        # LOGON_USER is served by IIS, and is the name of the
        # user after having been mapped to a local account.
        # Both IIS and Apache set REMOTE_USER, when possible.
        cherrypy.request.login = (environ.get('LOGON_USER')
                                  or environ.get('REMOTE_USER') or None)
        cherrypy.request.multithread = environ['wsgi.multithread']
        cherrypy.request.multiprocess = environ['wsgi.multiprocess']
        cherrypy.server.request(environ.get('REMOTE_ADDR', ''),
                                environ.get('REMOTE_ADDR', ''),
                                requestLine(environ),
                                translate_headers(environ),
                                environ['wsgi.input'],
                                environ['wsgi.url_scheme'],
                                )
    except:
        tb = _cputil.formatExc()
        cherrypy.log(tb)
        s, h, b = _cphttptools.bareError(tb)
        exc = sys.exc_info()
    else:
        resp = cherrypy.response
        s, h, b = resp.status, resp.headers, resp.body
        exc = None
    
    try:
        start_response(s, h, exc)
        for chunk in b:
            # WSGI requires all data to be of type "str". This coercion should
            # not take any time at all if chunk is already of type "str".
            # If it's unicode, it could be a big performance hit (x ~500).
            chunk = str(chunk)
            yield chunk
    except:
        tb = _cputil.formatExc()
        cherrypy.log(tb)
        s, h, b = _cphttptools.bareError(tb)
        # CherryPy test suite expects bareError body to be output,
        # so don't call start_response (which, according to PEP 333,
        # may raise its own error at that point).
        for chunk in b:
            yield str(chunk)



# Server components.
# _cpwsgiserver should not reference CherryPy in any way, so that it can
# be used in other frameworks and applications. Therefore, we wrap it here.

class WSGIServer(_cpwsgiserver.CherryPyWSGIServer):
    def __init__(self):
        conf = cherrypy.config.get
        _cpwsgiserver.CherryPyWSGIServer.__init__(self,
                                                  (conf("server.socketHost"),
                                                   conf("server.socketPort")),
                                                  wsgiApp,
                                                  conf("server.threadPool"),
                                                  conf("server.socketHost"))
