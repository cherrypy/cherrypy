"""Basic tests for the CherryPy core: request handling."""

from cherrypy.test import test
test.prefer_parent_path()

import cherrypy


def setup_server():
    
    from cherrypy.lib import safemime
    safemime.init()
    
    class Root:
        
        def flashupload(self, Filedata, Upload, Filename):
            return ("Upload: %r, Filename: %r, Filedata: %r" %
                    (Upload, Filename, Filedata.file.read()))
        flashupload.exposed = True
        flashupload._cp_config = {'tools.safe_multipart.on': True}
    
    cherrypy.config.update({
        'environment': 'test_suite',
        'server.max_request_body_size': 0,
        })
    cherrypy.tree.mount(Root())


#                             Client-side code                             #

from cherrypy.test import helper

class SafeMultipartHandlingTest(helper.CPWebCase):
    
    def test_Flash_Upload(self):
        headers = [
            ('Accept', 'text/*'),
            ('Content-Type', 'multipart/form-data; '
                 'boundary=----------KM7Ij5cH2KM7Ef1gL6ae0ae0cH2gL6'),
            ('User-Agent', 'Shockwave Flash'),
            ('Host', 'www.example.com:8080'),
            ('Content-Length', '499'),
            ('Connection', 'Keep-Alive'),
            ('Cache-Control', 'no-cache'),
            ]
        filedata = ('<?xml version="1.0" encoding="UTF-8"?>\r\n'
                    '<projectDescription>\r\n'
                    '</projectDescription>\r\n')
        body = (
            '------------KM7Ij5cH2KM7Ef1gL6ae0ae0cH2gL6\r\n'
            'Content-Disposition: form-data; name="Filename"\r\n'
            '\r\n'
            '.project\r\n'
            '------------KM7Ij5cH2KM7Ef1gL6ae0ae0cH2gL6\r\n'
            'Content-Disposition: form-data; '
                'name="Filedata"; filename=".project"\r\n'
            'Content-Type: application/octet-stream\r\n'
            '\r\n'
            + filedata + 
            '\r\n'
            '------------KM7Ij5cH2KM7Ef1gL6ae0ae0cH2gL6\r\n'
            'Content-Disposition: form-data; name="Upload"\r\n'
            '\r\n'
            'Submit Query\r\n'
            # Flash apps omit the trailing \r\n on the last line:
            '------------KM7Ij5cH2KM7Ef1gL6ae0ae0cH2gL6--'
            )
        self.getPage('/flashupload', headers, "POST", body)
        self.assertBody("Upload: 'Submit Query', Filename: '.project', "
                        "Filedata: %r" % filedata)


if __name__ == '__main__':
    setup_server()
    helper.testmain()
