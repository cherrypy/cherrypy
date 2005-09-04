"""Tutorial: http errors """

import cherrypy


class HTTPErrorDemo(object):
    
    def index(self):
        return """
        <html><body>
            <p>Edit tutorial.conf to turn on tracebacks</p>
            <a href="/error?code=400">400</a>
            <a href="/error?code=401">401</a>
            <a href="/error?code=402">402</a>
            <a href="/error?code=404">404</a>
        </body></html>
        """
    index.exposed = True
    
    def error(self, code):
        code = int(code)
        HTTPClientError = cherrypy._cperror.HTTPClientError
        
        raise HTTPClientError(status = int(code))
    error.exposed = True

cherrypy.root = HTTPErrorDemo()

if __name__ == '__main__':
    # Use the configuration file tutorial.conf.
    cherrypy.config.update(file = 'tutorial.conf')
    # Start the CherryPy server.
    cherrypy.server.start()
