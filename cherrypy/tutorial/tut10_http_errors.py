"""Tutorial: http errors """

import cherrypy


class HTTPErrorDemo(object):
    
    def index(self):
        # display some links that will result in errors
        tracebacks = cherrypy.config.get('server.showTracebacks')
        if tracebacks:
            trace = 'off'
        else:
            trace = 'on'
            
        return """
        <html><body>
            <a href="toggleTracebacks">Toggle tracebacks %s</a><br/><br/>
            <a href="/doesNotExist">Click me i'm a broken link!</a>
            <br/><br/>
            These errors are explicitly raised by the application.
            <a href="/error?code=400">400</a>
            <a href="/error?code=401">401</a>
            <a href="/error?code=402">402</a>
            <a href="/error?code=500">500</a>
        </body></html>
        """ % trace
    index.exposed = True

    def toggleTracebacks(self):
        # simple function to toggle tracebacks on and off 
        tracebacks = cherrypy.config.get('server.showTracebacks')
        cherrypy.config.update({'server.showTracebacks': not tracebacks})
        
        # redirect back to the index
        raise cherrypy._cperror.HTTPRedirect('/')
    toggleTracebacks.exposed=True
    
    def error(self, code):
        # raise an error based on the get query
        code = int(code)
        HTTPClientError = cherrypy._cperror.HTTPClientError
        raise HTTPClientError(status = code)
    error.exposed = True

cherrypy.root = HTTPErrorDemo()

if __name__ == '__main__':
    # Use the configuration file tutorial.conf.
    cherrypy.config.update(file = 'tutorial.conf')
    # Start the CherryPy server.
    cherrypy.server.start()
