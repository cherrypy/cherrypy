"""
Tutorial 01 - Hello World

The most basic (working) CherryPy application possible.
"""

# Import CherryPy global namespace
from cherrypy import cpg

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

# CherryPy always starts with cpg.root when trying to map request URIs
# to objects, so we need to mount a request handler object here. A request
# to '/' will be mapped to cpg.root.index().
cpg.root = HelloWorld()

# Start the CherryPy server using the configuration file tutorial.conf.
cpg.server.start(configFile = 'tutorial.conf')

