"""
Tutorial - Hello World

The most basic (working) CherryPy application possible.
"""

# Import CherryPy global namespace
import cherrypy

class HelloWorld:
    """ Sample request handler class. """

    def index(self):
        # CherryPy will call this method for the root URI ("/") and send
        # its return value to the client. Because this is tutorial
        # lesson number 01, we'll just send something really simple.
        # How about...
        return "Hello world!"

    # Expose the index method through the web. CherryPy will never
    # publish methods that don't have the exposed attribute set to True.
    index.exposed = True

# CherryPy always starts with app.root when trying to map request URIs
# to objects, so we need to mount a request handler object here. A request
# to '/' will be mapped to HelloWorld().index().
cherrypy.tree.mount(HelloWorld())

if __name__ == '__main__':
    # Start the CherryPy server.
    cherrypy.config.update(os.path.join(os.path.dirname(__file__), 'tutorial.conf'))
    cherrypy.server.start()
    cherrypy.engine.start()

