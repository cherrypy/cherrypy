"""Tests for managing HTTP issues (malformed requests, etc)."""

from httplib import HTTPConnection, HTTPSConnection
import mimetypes

import cherrypy


def encode_multipart_formdata(files):
    """Return (content_type, body) ready for httplib.HTTP instance.
    
    files: a sequence of (name, filename, value) tuples for multipart uploads.
    """
    BOUNDARY = '________ThIs_Is_tHe_bouNdaRY_$'
    L = []
    for key, filename, value in files:
        L.append('--' + BOUNDARY)
        L.append('Content-Disposition: form-data; name="%s"; filename="%s"' %
                 (key, filename))
        ct = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        L.append('Content-Type: %s' % ct)
        L.append('')
        L.append(value)
    L.append('--' + BOUNDARY + '--')
    L.append('')
    body = '\r\n'.join(L)
    content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
    return content_type, body




from cherrypy.test import helper

class HTTPTests(helper.CPWebCase):
    @staticmethod
    def setup_server():
        class Root:
            def index(self, *args, **kwargs):
                return "Hello world!"
            index.exposed = True
            
            def no_body(self, *args, **kwargs):
                return "Hello world!"
            no_body.exposed = True
            no_body._cp_config = {'request.process_request_body': False}
            
            def post_multipart(self, file):
                """Return a summary ("a * 65536\nb * 65536") of the uploaded file."""
                contents = file.file.read()
                summary = []
                curchar = ""
                count = 0
                for c in contents:
                    if c == curchar:
                        count += 1
                    else:
                        if count:
                            summary.append("%s * %d" % (curchar, count))
                        count = 1
                        curchar = c
                if count:
                    summary.append("%s * %d" % (curchar, count))
                return ", ".join(summary)
            post_multipart.exposed = True
        
        cherrypy.tree.mount(Root())
        cherrypy.config.update({'server.max_request_body_size': 30000000})
    
    def test_malformed_header(self):
        if self.scheme == 'https':
            c = HTTPSConnection('%s:%s' % (self.interface(), self.PORT))
        else:
            c = HTTPConnection('%s:%s' % (self.interface(), self.PORT))
        c.putrequest('GET', '/')
        c.putheader('Content-Type', 'text/plain')
        # See http://www.cherrypy.org/ticket/941 
        c._output('Re, 1.2.3.4#015#012')
        c.endheaders()
        
        response = c.getresponse()
        self.status = str(response.status)
        self.assertStatus(400)
        self.body = response.fp.read()
        self.assertBody("Illegal header line.")

