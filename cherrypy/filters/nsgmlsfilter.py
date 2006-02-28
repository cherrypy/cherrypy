import os, cgi

import cherrypy
from basefilter import BaseFilter


class NsgmlsFilter(BaseFilter):
    """Filter that runs the response through Nsgmls.
    """
    
    def before_finalize(self):
        if not cherrypy.config.get('nsgmls_filter.on', False):
            return
        
        # the tidy filter, by its very nature it's not generator friendly, 
        # so we just collect the body and work with it.
        original_body = cherrypy.response.collapse_body()
        
        fct = cherrypy.response.headers.get('Content-Type', '')
        ct = fct.split(';')[0]
        encoding = ''
        i = fct.find('charset=')
        if i != -1:
            encoding = fct[i+8:]
        if ct == 'text/html':
            # Remove bits of Javascript (nsgmls doesn't seem to handle
            #   them correctly (for instance, if <a appears in your
            #   Javascript code nsgmls complains about it)
            while True:
                i = original_body.find('<script')
                if i == -1:
                    break
                j = original_body.find('</script>', i)
                if j == -1:
                    break
                original_body = original_body[:i] + original_body[j+9:]

            tmpdir = cherrypy.config.get('nsgmls_filter.tmp_dir')
            page_file = os.path.join(tmpdir, 'page.html')
            err_file = os.path.join(tmpdir, 'nsgmls.err')
            f = open(page_file, 'wb')
            f.write(original_body)
            f.close()
            nsgmls_path = cherrypy.config.get('nsgmls_filter.nsgmls_path')
            catalog_path = cherrypy.config.get('nsgmls_filter.catalog_path')
            command = '%s -c%s -f%s -s -E10 %s' % (
                nsgmls_path, catalog_path, err_file, page_file)
            command = command.replace('\\', '/')
            os.system(command)
            f = open(err_file, 'rb')
            err = f.read()
            f.close()
            errs = err.splitlines()
            new_errs = []
            for err in errs:
                ignore = False
                for err_ign in cherrypy.config.get('nsgmls_filter.errors_to_ignore', []):
                    if err.find(err_ign) != -1:
                        ignore = True
                        break
                if not ignore:
                    new_errs.append(err)
            if new_errs:
                new_body = "Wrong HTML:<br />" + cgi.escape('\n'.join(new_errs)).replace('\n','<br />')
                new_body += '<br /><br />'
                i = 0
                for line in original_body.splitlines():
                    i += 1
                    new_body += "%03d - "%i + cgi.escape(line).replace('\t','    ').replace(' ','&nbsp;') + '<br />'
                
                cherrypy.response.body = new_body

