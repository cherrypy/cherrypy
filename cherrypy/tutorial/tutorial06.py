"""
Tutorial 06 - Aspects

CherryPy2 aspects let you dynamically alter a request handler object's
behaviour by adding code that gets executed before and/or after
requested methods. This is useful in situations where you need common
method behavior across multiple methods or even objects (aspects can
be part of derived classes).
"""

from cherrypy import cpg

# We need to import some additional stuff for our aspect code.
from cherrypy.lib.aspect import Aspect, STOP, CONTINUE


class Page(Aspect):
    title = 'Untitled Page'

    def header(self):
        # this is the same as in tutorial05.py
        return '''
            <html>
            <head>
                <title>%s</title>
            <head>
            <body>
            <h2>%s</h2>
        ''' % (self.title, self.title)

    def footer(self):
        # this is the same as in tutorial05.py
        return '''
            </body>
            </html>
        '''

    def _before(self, methodName, method):
        # The _before aspect method gets executed whenever *any*
        # other method is called, including header and footer -- which
        # is something we don't want, so we check the called method
        # first.
        if methodName not in ['header', 'footer']:
            return CONTINUE, self.header()
        else:
            return CONTINUE, ''

    def _after(self, methodName, method):
        # Same as above, except _after gets called after the actually
        # requested method was executed. Its results are appended to
        # the output string.
        if methodName not in ['header', 'footer']:
            return CONTINUE, self.footer()
        else:
            return CONTINUE, ''



class HomePage(Page):
    title = 'Tutorial 6 -- Aspect Powered!'

    def __init__(self):
        self.another = AnotherPage()

    def index(self):
        # Note that we don't call the header and footer methods
        # anymore! The aspect methods inherited from the Page class
        # take care of that now.
        return '''
            <p>
            Isn't this exciting? There's
            <a href="./another/">another page</a>, too!
            </p>
        '''

    index.exposed = True


class AnotherPage(Page):
    title = 'Another Page'

    def index(self):
        # See above. No header or footer methods called!
        return '''
            <p>
            And this is the amazing second page!
            </p>
        '''

    index.exposed = True


cpg.root = HomePage()

cpg.server.start(configFile = 'tutorial.conf')
