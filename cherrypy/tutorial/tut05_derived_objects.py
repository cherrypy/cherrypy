"""
Tutorial - Object inheritance.

You are free to derive your request handler classes from any base
class you wish. In most real-world applications, you will probably
want to create a central base class used for all your pages, which takes
care of things like printing a common page header and footer.
"""

import os.path

import cherrypy


class Page:
    """Web page base class."""

    # Store the page title in a class attribute
    title = 'Untitled Page'

    def header(self):
        """Render HTML layout header."""
        return """
            <html>
            <head>
                <title>%s</title>
            <head>
            <body>
            <h2>%s</h2>
        """ % (self.title, self.title)

    def footer(self):
        """Render HTML layout footer."""
        return """
            </body>
            </html>
        """

    # Note that header and footer don't get their exposed attributes
    # set to True. This isn't necessary since the user isn't supposed
    # to call header or footer directly; instead, we'll call them from
    # within the actually exposed handler methods defined in this
    # class' subclasses.


class HomePage(Page):
    """Home page app."""

    # Different title for this page
    title = 'Tutorial 5'

    def __init__(self):
        """Mount another page into the home page app."""
        # create a subpage
        self.another = AnotherPage()

    @cherrypy.expose
    def index(self):
        """Produce HTTP response body of home page app index URI."""
        # Note that we call the header and footer methods inherited
        # from the Page class!
        return (
            self.header()
            + """
            <p>
            Isn't this exciting? There's
            <a href="./another/">another page</a>, too!
            </p>
        """
            + self.footer()
        )


class AnotherPage(Page):
    """Another page app."""

    title = 'Another Page'

    @cherrypy.expose
    def index(self):
        """Produce HTTP response body of another page app index URI."""
        return (
            self.header()
            + """
            <p>
            And this is the amazing second page!
            </p>
        """
            + self.footer()
        )


tutconf = os.path.join(os.path.dirname(__file__), 'tutorial.conf')

if __name__ == '__main__':
    # CherryPy always starts with app.root when trying to map request URIs
    # to objects, so we need to mount a request handler root. A request
    # to '/' will be mapped to HelloWorld().index().
    cherrypy.quickstart(HomePage(), config=tutconf)
