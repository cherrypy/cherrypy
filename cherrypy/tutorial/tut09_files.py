"""

Tutorial: File upload and download

Uploads
-------

When a client uploads a file to a CherryPy application, it's placed
on disk immediately. CherryPy will pass it to your exposed method
as an argument (see "myFile" below); that arg will have a "file"
attribute, which is a handle to the temporary uploaded file.
If you wish to permanently save the file, you need to read()
from myFile.file and write() somewhere else.

Note the use of 'enctype="multipart/form-data"' and 'input type="file"'
in the HTML which the client uses to upload the file.


Downloads
---------

If you wish to send a file to the client, you have two options:
First, you can simply return a file-like object from your page handler.
CherryPy will read the file and serve it as the content (HTTP body)
of the response. However, that doesn't tell the client that
the response is a file to be saved, rather than displayed.
Use cherrypy.lib.cptools.serveFile for that; it takes four
arguments:

serveFile(path, contentType=None, disposition=None, name=None)

Set "name" to the filename that you expect clients to use when they save
your file. Note that the "name" argument is ignored if you don't also
provide a "disposition" ("application/x-download" works in most cases).

"""

import os
localDir = os.path.dirname(__file__)
absDir = os.path.join(os.getcwd(), localDir)

import cherrypy
from cherrypy.lib import cptools


class FileDemo(object):
    
    def index(self):
        return """
        <html><body>
            <form action="upload" method="post" enctype="multipart/form-data">
            filename: <input type="file" name="myFile" /><br />
            <input type="submit" />
            </form>
        </body></html>
        """
    index.exposed = True
    
    def upload(self, myFile):
        out = """<html>
        <body>
            myFile length: %s<br />
            myFile filename: %s<br />
            myFile mime-type: %s
        </body>
        </html>"""
        
        # Although this just counts the file length, it demonstrates
        # how to read large files in chunks instead of all at once.
        # CherryPy uses Python's cgi module to read the uploaded file
        # into a temporary file; myFile.file.read reads from that.
        size = 0
        while True:
            data = myFile.file.read(8192)
            if not data:
                break
            size += len(data)
        
        return out % (size, myFile.filename, myFile.type)
    upload.exposed = True
    
    def download(self):
        path = os.path.join(absDir, "pdf_file.pdf")
        return cptools.serveFile(path, "application/x-download",
                                 "attachment", os.path.basename(path))
    download.exposed = True


cherrypy.root = FileDemo()

if __name__ == '__main__':
    # Use the configuration file tutorial.conf.
    cherrypy.config.update(file = 'tutorial.conf')
    # Start the CherryPy server.
    cherrypy.server.start()
