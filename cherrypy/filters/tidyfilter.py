import cgi
import os
import StringIO
import traceback

import cherrypy
from basefilter import BaseFilter


class TidyFilter(BaseFilter):
    """Filter that runs the response through Tidy.
    
    Note that we use the standalone Tidy tool rather than the python
    mxTidy module. This is because this module doesn't seem to be
    stable and it crashes on some HTML pages (which means that the
    server would also crash)
    """
    
    def beforeFinalize(self):
        if not cherrypy.config.get('tidyFilter.on', False):
            return
        
        # the tidy filter, by its very nature it's not generator friendly, 
        # so we just collect the body and work with it.
        originalBody = ''.join([chunk for chunk in cherrypy.response.body])
        cherrypy.response.body = [originalBody]
        
        fct = cherrypy.response.headerMap.get('Content-Type', '')
        ct = fct.split(';')[0]
        encoding = ''
        i = fct.find('charset=')
        if i != -1:
            encoding = fct[i+8:]
        if ct == 'text/html':
            tmpdir = cherrypy.config.get('tidyFilter.tmpDir')
            pageFile = os.path.join(tmpdir, 'page.html')
            outFile = os.path.join(tmpdir, 'tidy.out')
            errFile = os.path.join(tmpdir, 'tidy.err')
            f = open(pageFile, 'wb')
            f.write(originalBody)
            f.close()
            tidyEncoding = encoding.replace('-', '')
            if tidyEncoding:
                tidyEncoding = '-' + tidyEncoding
            
            strictXml = ""
            if cherrypy.config.get('tidyFilter.strictXml', False):
                strictXml = ' -xml'
            os.system('"%s" %s%s -f %s -o %s %s' %
                      (cherrypy.config.get('tidyFilter.tidyPath'), tidyEncoding,
                       strictXml, errFile, outFile, pageFile))
            f = open(errFile, 'rb')
            err = f.read()
            f.close()
            
            errList = err.splitlines()
            newErrList = []
            for err in errList:
                if (err.find('Warning') != -1 or err.find('Error') != -1):
                    ignore = 0
                    for errIgn in cherrypy.config.get('encodingFilter.errorsToIgnore', []):
                        if err.find(errIgn) != -1:
                            ignore = 1
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
                
                cherrypy.response.body = [newBody]

            elif strictXml:
                # The HTML is OK, but is it valid XML
                # Use elementtree to parse XML
                from elementtree.ElementTree import parse
                tagList = ['nbsp', 'quot']
                for tag in tagList:
                    originalBody = originalBody.replace(
                        '&' + tag + ';', tag.upper())

                if encoding:
                    originalBody = """<?xml version="1.0" encoding="%s"?>""" % encoding + originalBody
                f = StringIO.StringIO(originalBody)
                try:
                    tree = parse(f)
                except:
                    # Wrong XML
                    bodyFile = StringIO.StringIO()
                    traceback.print_exc(file = bodyFile)
                    cherrypy.response.body = [bodyFile.getvalue()]
                    
                    newBody = "Wrong XML:<br />" + cgi.escape(bodyFile.getvalue().replace('\n','<br />'))
                    newBody += '<br /><br />'
                    i = 0
                    for line in originalBody.splitlines():
                        i += 1
                        newBody += "%03d - "%i + cgi.escape(line).replace('\t','    ').replace(' ','&nbsp;') + '<br />'
                    
                    cherrypy.response.body = [newBody]

