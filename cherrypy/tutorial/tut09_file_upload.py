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
        return """
        <html><body>
            myFile length: %s<br />
            myFile filename: %s<br />
            myFile mime-type: %s
        </body></html>
        """ % (len(myFile.value),
               myFile.filename,
               myFile.type)
    upload.exposed = True


cherrypy.root = FileUploadDemo()

if __name__ == '__main__':
    # Use the configuration file tutorial.conf.
    cherrypy.config.update(file = 'tutorial.conf')
    # Start the CherryPy server.
    cherrypy.server.start()
