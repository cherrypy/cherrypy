***************
Uploading Files
***************

When a client uploads a file to a CherryPy application, it's placed
on disk immediately. CherryPy will pass it to your exposed method
as an argument (see "myFile" below); that arg will have a "file"
attribute, which is a handle to the temporary uploaded file.
If you wish to permanently save the file, you need to read()
from myFile.file and write() somewhere else.

Note the use of 'enctype="multipart/form-data"' and 'input type="file"'
in the HTML which the client uses to upload the file.


Here is a simple example that shows how file uploads are handled by CherryPy::

	import os
	localDir = os.path.dirname(__file__)
	absDir = os.path.join(os.getcwd(), localDir)

	import cherrypy

	class FileDemo(object):
	    
	    def index(self):
		return """
		<html><body>
		    <h2>Upload a file</h2>
		    <form action="upload" method="post" enctype="multipart/form-data">
		    filename: <input type="file" name="myFile" /><br />
		    <input type="submit" />
		    </form>
		    <h2>Download a file</h2>
		    <a href='download'>This one</a>
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
		# CherryPy reads the uploaded file into a temporary file;
		# myFile.file.read reads from that.
		size = 0
		while True:
		    data = myFile.file.read(8192)
		    if not data:
		        break
		    size += len(data)
		
		return out % (size, myFile.filename, myFile.content_type)
	    upload.exposed = True
	    


	tutconf = os.path.join(os.path.dirname(__file__), 'tutorial.conf')

	if __name__ == '__main__':
	    # CherryPy always starts with app.root when trying to map request URIs
	    # to objects, so we need to mount a request handler root. A request
	    # to '/' will be mapped to HelloWorld().index().
	    cherrypy.quickstart(FileDemo(), config=tutconf)
	else:
	    # This branch is for the test suite; you can ignore it.
	    cherrypy.tree.mount(FileDemo(), config=tutconf)






