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
from basefilter import BaseFilter

class NsgmlsFilter(BaseFilter):
    """Filter that runs the response through Nsgmls.
    """
    
    def beforeFinalize(self):
        # We have to dynamically import cpg because Python can't handle
        #   circular module imports :-(
        global cpg
        from cherrypy import cpg
        
        if not cpg.config.get('nsgmlsFilter.on', False):
            return
        
        # the tidy filter, by its very nature it's not generator friendly, 
        # so we just collect the body and work with it.
        originalBody = ''.join(cpg.response.body)
        cpg.response.body = [originalBody]
        
        fct = cpg.response.headerMap.get('Content-Type', '')
        ct = fct.split(';')[0]
        encoding = ''
        i = fct.find('charset=')
        if i != -1:
            encoding = fct[i+8:]
        if ct == 'text/html':
            tmpdir = cpg.config.get('nsgmlsFilter.tmpDir')
            pageFile = os.path.join(tmpdir, 'page.html')
            errFile = os.path.join(tmpdir, 'nsgmls.err')
            f = open(pageFile, 'wb')
            f.write(originalBody)
            f.close()
            nsgmlsEncoding = encoding.replace('-', '')
            nsgmlsPath = cpg.config.get('nsgmlsFilter.nsgmlsPath')
            catalogPath = cpg.config.get('nsgmlsFilter.catalogPath')
            command = '%s -c%s -f%s -s -E10 %s' % (
                nsgmlsPath, catalogPath, errFile, pageFile)
            command = command.replace('\\', '/')
            os.system(command)
            f = open(errFile, 'rb')
            err = f.read()
            f.close()
            errList = err.splitlines()
            newErrList = []
            for err in errList:
                ignore = False
                for errIgn in cpg.config.get('nsgmlsFilter.errorsToIgnore', []):
                    if err.find(errIgn) != -1:
                        ignore = True
                        break
                if not ignore:
                    newErrList.append(err)
            if newErrList:
                newBody = "Wrong HTML:<br />" + cgi.escape('\n'.join(newErrList)).replace('\n','<br />')
                newBody += '<br /><br />'
                i = 0
                for line in originalBody.splitlines():
                    i += 1
                    newBody += "%03d - "%i + cgi.escape(line).replace('\t','    ').replace(' ','&nbsp;') + '<br />'
                
                cpg.response.body = [newBody]


