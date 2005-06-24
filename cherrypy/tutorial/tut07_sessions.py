"""
Tutorial 08 - Sessions

Storing session data in CherryPy applications is very easy: cpg.request
provides a dictionary called sessionMap that represents the session
data for the current user. If you use RAM based sessions, you can store
any kind of object into that dictionary; otherwise, you are limited to
objects that can be pickled.
"""

from cherrypy import cpg


class HitCounter:
    def index(self):
        # Increase the silly hit counter
        count = cpg.sessions.default.get('count', 0) + 1
        
        # Store the new value in the session dictionary
        cpg.sessions.default['count'] = count
        
        # And display a silly hit count message!
        return '''
            During your current session, you've viewed this
            page %s times! Your life is a patio of fun!
        ''' % count
    index.exposed = True


cpg.root = HitCounter()
cpg.config.update({'global': {'sessionFilter.on': True}})

if __name__ == '__main__':
    cpg.config.update(file = 'tutorial.conf')
    cpg.server.start()

