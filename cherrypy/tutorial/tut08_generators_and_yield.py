"""
Bonus Tutorial: Using generators to return result bodies

Instead of returning a complete result string, you can use the yield
statement to return one result part after another. This may be convenient
in situations where using a template package like CherryPy or Cheetah
would be overkill, and messy string concatenation too uncool. ;-)
"""

import cherrypy


class GeneratorDemo:
    
    def header(self):
        return "<html><body><h2>Generators rule!</h2>"
    
    def footer(self):
        return "</body></html>"
    
    def index(self):
        # Let's make up a list of users for presentation purposes
        users = ['Remi', 'Carlos', 'Hendrik', 'Lorenzo Lamas']
        
        # Every yield line adds one part to the total result body.
        yield self.header()
        yield "<h3>List of users:</h3>"
        
        for user in users:
            yield "%s<br/>" % user
            
        yield self.footer()
    index.exposed = True

cherrypy.root = GeneratorDemo()


if __name__ == '__main__':
    cherrypy.config.update(file = 'tutorial.conf')
    cherrypy.server.start()
    cherrypy.engine.start()

