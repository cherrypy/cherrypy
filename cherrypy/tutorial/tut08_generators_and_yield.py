"""
Bonus Tutorial: Using generators to return result bodies.

Instead of returning a complete result string, you can use the yield
statement to return one result part after another. This may be convenient
in situations where using a template package like CherryPy or Cheetah
would be overkill, and messy string concatenation too uncool. ;-)
"""

import os.path

import cherrypy


class GeneratorDemo:
    """HTTP response streaming app."""

    def header(self):
        """Render HTML layout header."""
        return "<html><body><h2>Generators rule!</h2>"

    def footer(self):
        """Render HTML layout footer."""
        return "</body></html>"

    @cherrypy.expose
    def index(self):
        """Stream HTTP response body of generator app index URI."""
        # Let's make up a list of users for presentation purposes
        users = ["Remi", "Carlos", "Hendrik", "Lorenzo Lamas"]

        # Every yield line adds one part to the total result body.
        yield self.header()
        yield "<h3>List of users:</h3>"

        for user in users:
            yield "%s<br/>" % user

        yield self.footer()


tutconf = os.path.join(os.path.dirname(__file__), "tutorial.conf")

if __name__ == "__main__":
    # CherryPy always starts with app.root when trying to map request URIs
    # to objects, so we need to mount a request handler root. A request
    # to '/' will be mapped to HelloWorld().index().
    cherrypy.quickstart(GeneratorDemo(), config=tutconf)
