"""Tutorial: File upload"""

from cherrypy import cpg

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
        """ % (len(myFile),
               cpg.request.filenameMap['myFile'],
               cpg.request.fileTypeMap['myFile'])
    upload.exposed = True


cpg.root = FileUploadDemo()

if __name__ == '__main__':
    # Use the configuration file tutorial.conf.
    cpg.config.update(file = 'tutorial.conf')
    # Start the CherryPy server.
    cpg.server.start()
