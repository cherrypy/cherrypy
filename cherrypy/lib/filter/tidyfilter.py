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

import os, cgi
from basefilter import BaseOutputFilter
from cherrypy import cpg
import HTMLParser

class TidyFilter(BaseOutputFilter):
    """
    Filter that runs the response through Tidy.
    Note that we use the standalone Tidy tool rather than the python
    mxTidy module. This is because this module doesn't seem to be
    stable and it crashes on some HTML pages (which means that the
    server would also crash)
    """

    def __init__(self, tidyPath, tmpDir, strictXml = False, errorsToIgnore = []):
        self.tidyPath = tidyPath
        self.tmpDir = tmpDir
        self.strictXml = strictXml
        self.errorsToIgnore = errorsToIgnore

    def beforeResponse(self):
        # the tidy filter, by its very nature it's not generator friendly, 
        # so we just collect the body and work with it.
        originalBody = ''.join(cpg.response.body)
        cpg.response.body = [originalBody]
        p = HTMLParser.HTMLParser()
        p.feed(originalBody)
        
        fct = cpg.response.headerMap.get('Content-Type', '')
        ct = fct.split(';')[0]
        if ct == 'text/html':
            pageFile = os.path.join(self.tmpDir, 'page.html')
            outFile = os.path.join(self.tmpDir, 'tidy.out')
            errFile = os.path.join(self.tmpDir, 'tidy.err')
            f = open(pageFile, 'wb')
            f.write(originalBody)
            f.close()
            encoding = ''
            i = fct.find('charset=')
            if i != -1:
                encoding = fct[i+8:]
            encoding = encoding.replace('utf-8', 'utf8')
            if encoding:
                encoding = '-' + encoding
            strictXml = ""
            if self.strictXml:
                strictXml = ' -xml'
            os.system('"%s" %s%s -f %s -o %s %s' % (
                self.tidyPath, encoding, strictXml, errFile, outFile, pageFile))
            f = open(errFile, 'rb')
            err = f.read()
            f.close()

            errList = err.splitlines()
            newErrList = []
            for err in errList:
                if (err.find('Warning') != -1 or err.find('Error') != -1):
                    ignore = 0
                    for errIgn in self.errorsToIgnore:
                        if err.find(errIgn) != -1:
                            ignore = 1
                            break
                    if not ignore: newErrList.append(err)

            if newErrList:
                newBody = "Wrong HTML:<br>" + cgi.escape('\n'.join(newErrList)).replace('\n','<br>')
                newBody += '<br><br>'
                i=0
                for line in originalBody.splitlines():
                    i += 1
                    newBody += "%03d - "%i + cgi.escape(line).replace('\t','    ').replace(' ','&nbsp;') + '<br>'

                cpg.response.body = [newBody]
