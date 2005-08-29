"""Tutorial: File upload"""

import cherrypy


class FileUploadDemo(object):
    
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


cherrypy.root = FileUploadDemo()

if __name__ == '__main__':
    # Use the configuration file tutorial.conf.
    cherrypy.config.update(file = 'tutorial.conf')
    # Start the CherryPy server.
    cherrypy.server.start()
