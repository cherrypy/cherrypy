"""Functions to run cherrypy.response through Tidy or NSGML."""

import cgi
import os
import StringIO
import traceback


def tidy(temp_dir, tidy_path, strict_xml=False, errors_to_ignore=None):
    """Run cherrypy.response through Tidy.
    
    Note that we use the standalone Tidy tool rather than the python
    mxTidy module. This is because this module doesn't seem to be
    stable and it crashes on some HTML pages (which means that the
    server would also crash)
    """
    # the tidy tool, by its very nature it's not generator friendly, 
    # so we just collapse the body and work with it.
    orig_body = cherrypy.response.collapse_body()
    
    fct = cherrypy.response.headers.get('Content-Type', '')
    ct = fct.split(';')[0]
    encoding = ''
    i = fct.find('charset=')
    if i != -1:
        encoding = fct[i + 8:]
    
    if ct == 'text/html':
        page_file = os.path.join(temp_dir, 'page.html')
        open(page_file, 'wb').write(orig_body)
        
        out_file = os.path.join(temp_dir, 'tidy.out')
        err_file = os.path.join(temp_dir, 'tidy.err')
        tidy_enc = encoding.replace('-', '')
        if tidy_enc:
            tidy_enc = '-' + tidy_enc
        
        strict_xml = (" -xml", "")[bool(strict_xml)]
        os.system('"%s" %s%s -f %s -o %s %s' %
                  (tidy_path, tidy_enc, strict_xml,
                   err_file, out_file, page_file))
        errs = open(err_file, 'rb').read()
        
        new_errs = []
        for err in errs.splitlines():
            if (err.find('Warning') != -1 or err.find('Error') != -1):
                ignore = 0
                for err_ign in errors_to_ignore or []:
                    if err.find(err_ign) != -1:
                        ignore = 1
                        break
                if not ignore:
                    new_errs.append(err)
        
        if new_errs:
            cherrypy.response.body = wrong_content('<br />'.join(new_errs),
                                                   orig_body)
        elif strict_xml:
            # The HTML is OK, but is it valid XML?
            # Use elementtree to parse XML
            from elementtree.ElementTree import parse
            tag_list = ['nbsp', 'quot']
            for tag in tag_list:
                orig_body = orig_body.replace('&' + tag + ';', tag.upper())
            
            if encoding:
                enctag = '<?xml version="1.0" encoding="%s"?>' % encoding
                orig_body = enctag + orig_body
            
            f = StringIO.StringIO(orig_body)
            try:
                tree = parse(f)
            except:
                # Wrong XML
                body_file = StringIO.StringIO()
                traceback.print_exc(file = body_file)
                body_file = '<br />'.join(body_file.getvalue())
                cherrypy.response.body = wrong_content(body_file, orig_body, "XML")

def html_space(text):
    """Escape text, replacing space with nbsp and tab with 4 nbsp's."""
    return cgi.escape(text).replace('\t', '    ').replace(' ', '&nbsp;')

def html_break(text):
    """Escape text, replacing newline with HTML br element."""
    return cgi.escape(text).replace('\n', '<br />')

def wrong_content(header, body, content_type="HTML"):
    output = ["Wrong %s:<br />%s<br />" % (content_type, html_break(header))]
    for i, line in enumerate(body.splitlines()):
        output.append("%03d - %s" % (i + 1, html_space(line)))
    return "<br />".join(output)


def nsgmls(temp_dir, nsgmls_path, catalog_path, errors_to_ignore=None):
    # the tidy tool, by its very nature it's not generator friendly, 
    # so we just collect the body and work with it.
    orig_body = cherrypy.response.collapse_body()
    
    fct = cherrypy.response.headers.get('Content-Type', '')
    ct = fct.split(';')[0]
    encoding = ''
    i = fct.find('charset=')
    if i != -1:
        encoding = fct[i + 8:]
    if ct == 'text/html':
        # Remove bits of Javascript (nsgmls doesn't seem to handle
        #   them correctly (for instance, if <a appears in your
        #   Javascript code nsgmls complains about it)
        while True:
            i = orig_body.find('<script')
            if i == -1:
                break
            j = orig_body.find('</script>', i)
            if j == -1:
                break
            orig_body = orig_body[:i] + orig_body[j+9:]

        page_file = os.path.join(temp_dir, 'page.html')
        open(page_file, 'wb').write(orig_body)
        
        err_file = os.path.join(temp_dir, 'nsgmls.err')
        command = ('%s -c%s -f%s -s -E10 %s' %
                   (nsgmls_path, catalog_path, err_file, page_file))
        command = command.replace('\\', '/')
        os.system(command)
        errs = open(err_file, 'rb').read()
        
        new_errs = []
        for err in errs.splitlines():
            ignore = False
            for err_ign in errors_to_ignore or []:
                if err.find(err_ign) != -1:
                    ignore = True
                    break
            if not ignore:
                new_errs.append(err)
        
        if new_errs:
            cherrypy.response.body = wrong_content('<br />'.join(new_errs),
                                                   orig_body)

