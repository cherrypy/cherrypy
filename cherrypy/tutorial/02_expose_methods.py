"""
Tutorial 02 - Multiple methods

This tutorial shows you how to link to other methods of your request
handler.
"""

from cherrypy import cpg

class HelloWorld:

    def index(self):
        # Let's link to another method here.
        return 'We have an <a href="showMessage">important message</a> for you!'

    index.exposed = True


    def showMessage(self):
        # Here's the important message!
        return "Hello world!"

    showMessage.exposed = True

cpg.root = HelloWorld()
cpg.server.start(configFile = 'tutorial.conf')
