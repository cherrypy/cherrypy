"""
Tutorial 03 - Passing variables

This tutorial shows you how to pass GET/POST variables to methods.
"""

from cherrypy import cpg

class WelcomePage:

    def index(self):
        # Ask for the user's name.
        return '''
            <form action="greetUser" method="GET">
            What is your name?
            <input type="text" name="name" />
            <input type="submit" />
            </form>
        '''

    index.exposed = True


    def greetUser(self, name = None):
        # CherryPy passes all GET and POST variables as method parameters.
        # It doesn't make a difference where the variables come from, how
        # large their contents are, and so on.
        #
        # You can define default parameter values as usual. In this
        # example, the "name" parameter defaults to None so we can check
        # if a name was actually specified.

        if name:
            # Greet the user!
            return "Hey %s, what's up?" % name
        else:
            # No name was specified
            return 'Please enter your name <a href="./">here</a>.'

    greetUser.exposed = True


cpg.root = WelcomePage()
cpg.config.loadConfigFile('tutorial.conf')
cpg.server.start()
