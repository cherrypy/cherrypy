"""
Tutorial - Multiple methods.

This tutorial shows you how to link to other methods of your request
handler.
"""

import os.path

import cherrypy


class HelloWorld:
    """Hello world app."""

    @cherrypy.expose
    def index(self):
        """Produce HTTP response body of hello world app index URI."""
        # Let's link to another method here.
        return 'We have an <a href="show_msg">important message</a> for you!'

    @cherrypy.expose
    def show_msg(self):
        """Render a "Hello world!" message on ``/show_msg`` URI."""
        return 'Hello world!'


tutconf = os.path.join(os.path.dirname(__file__), 'tutorial.conf')

if __name__ == '__main__':
    # CherryPy always starts with app.root when trying to map request URIs
    # to objects, so we need to mount a request handler root. A request
    # to '/' will be mapped to HelloWorld().index().
    cherrypy.quickstart(HelloWorld(), config=tutconf)
