"""Tests for managing HTTP issues (malformed requests, etc)."""

from cherrypy.test import test
test.prefer_parent_path()

import httplib
import cherrypy
import md5, mimetypes


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


def setup_server():
    
    class Root:
        def index(self, *args, **kwargs):
            return "Hello world!"
        index.exposed = True
        
        def post_multipart(self, file):
            # compute and return md5 of posted file
            contents = file.file.read()
            return md5.md5(contents).hexdigest()
        post_multipart.exposed = True
    
    cherrypy.tree.mount(Root())
    cherrypy.config.update({'environment': 'test_suite',
                            'server.max_request_body_size': 30000000})


from cherrypy.test import helper

class HTTPTests(helper.CPWebCase):
    
    def test_sockets(self):
        # By not including a Content-Length header, cgi.FieldStorage
        # will hang. Verify that CP times out the socket and responds
        # with 411 Length Required.
        c = httplib.HTTPConnection("127.0.0.1:%s" % self.PORT)
        c.request("POST", "/")
        self.assertEqual(c.getresponse().status, 411)
    
    def test_post_multipart(self):
        # generate file contents for a large post
        contents = "abcdefghijklmnopqrstuvwxyz" * 1000000
        post_md5 = md5.md5(contents).hexdigest()
        
        # encode as multipart form data
        files=[('file', 'file.txt', contents)]
        content_type, body = encode_multipart_formdata(files)
        
        # post file
        if self.scheme == 'https':
            c = httplib.HTTPS('127.0.0.1:%s' % self.PORT)
        else:
            c = httplib.HTTP('127.0.0.1:%s' % self.PORT)
        c.putrequest('POST', '/post_multipart')
        c.putheader('Content-Type', content_type)
        c.putheader('Content-Length', str(len(body)))
        c.endheaders()
        c.send(body)
        
        errcode, errmsg, headers = c.getreply()
        self.assertEqual(errcode, 200)
        
        response_body = c.file.read()
        self.assertEquals(post_md5, response_body)


if __name__ == '__main__':
    setup_server()
    helper.testmain()
