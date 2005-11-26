import os, cgi

import cherrypy
from basefilter import BaseFilter


class NsgmlsFilter(BaseFilter):
    """Filter that runs the response through Nsgmls.
    """
    
    def beforeFinalize(self):
        if not cherrypy.config.get('nsgmlsFilter.on', False):
            return
        
        # the tidy filter, by its very nature it's not generator friendly, 
        # so we just collect the body and work with it.
        originalBody = cherrypy.response.collapse_body()
        
        fct = cherrypy.response.headerMap.get('Content-Type', '')
        ct = fct.split(';')[0]
        encoding = ''
        i = fct.find('charset=')
        if i != -1:
            encoding = fct[i+8:]
        if ct == 'text/html':
            tmpdir = cherrypy.config.get('nsgmlsFilter.tmpDir')
            pageFile = os.path.join(tmpdir, 'page.html')
            errFile = os.path.join(tmpdir, 'nsgmls.err')
            f = open(pageFile, 'wb')
            f.write(originalBody)
            f.close()
            nsgmlsEncoding = encoding.replace('-', '')
            nsgmlsPath = cherrypy.config.get('nsgmlsFilter.nsgmlsPath')
            catalogPath = cherrypy.config.get('nsgmlsFilter.catalogPath')
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
                for errIgn in cherrypy.config.get('nsgmlsFilter.errorsToIgnore', []):
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
                
                cherrypy.response.body = newBody

