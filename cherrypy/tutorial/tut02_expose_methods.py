"""
Tutorial - Multiple methods.

This tutorial shows you how to link to other methods of your request
handler.
"""

import os.path

import cherrypy


class HelloWorld:
    """HelloWorld class for tutorial."""

    @cherrypy.expose
    def index(self):
        """
        Index HelloWorld.

        Let's link to another method here.
        """
        return 'We have an <a href="show_msg">important message</a> for you!'

    @cherrypy.expose
    def show_msg(self):
        """
        Show_msg HelloWorld.

        Here's the important message!
        """
        return 'Hello world!'


tutconf = os.path.join(os.path.dirname(__file__), 'tutorial.conf')

if __name__ == '__main__':
    # CherryPy always starts with app.root when trying to map request URIs
    # to objects, so we need to mount a request handler root. A request
    # to '/' will be mapped to HelloWorld().index().
    cherrypy.quickstart(HelloWorld(), config=tutconf)
