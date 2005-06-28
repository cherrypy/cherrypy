"""
Tutorial 10 - Advanced sessionFilter usage see tut10_sessionfilter.conf
"""

import cherrypy

class HitCounter:

    def __init__(self):
        # turn on the sessionfilter and create sessions for the admin
        # and forum sections of the site
        cherrypy.config.update(
                {
                'global' : {'sessionFilter.on': True},
                '/admin' : {'sessionFilter.sessionList' : ['admin'] },
                '/forum' : {'sessionFilter.sessionList' : ['forum'] }
                })

    # this is just a primative template function
    def __examplePage(self, poweredBy, count, links, sessionKey):
        yield '<html><head><title>sessionFilter example</title><body>\n'
        yield 'This page uses %s based session storage.<br/>\n' % poweredBy
        yield 'You have viewed this page %i times. <br/><br/>\n' % count
        for link in links:
            yield '<a href="/%s">%s</a>&nbsp;&nbsp;\n' % (link, link)

        yield '<br/><br/>The Current SessionKey is: &nbsp;&nbsp;\n'
        yield sessionKey
        yield '\n</body></html>'

    # a list of the pages used in the example so we can add pages
    # without changing any code
    samplePages = ['admin', 'index', 'forum']
    
    def index(self):
        # this function uses the default session
        # it may not be the defualt in future versions
        
        # Increase the silly hit counter
        count = cherrypy.sessions.default.get('count', 0) + 1

        # Store the new value in the session dictionary
        # cherrypy.sessions.default is available by default
        cherrypy.sessions.default['count'] = count

        # And display a silly hit count message!
        key = cherrypy.sessions.default.key
        return self.__examplePage('ram', count, self.samplePages, key)

    index.exposed = True

    def admin(self):
        # this function uses the admin which is defined in
        # the config file "tut10_sessionFilter.conf", otherwise
        # it mirrors the session function

        adminCount = cherrypy.sessions.admin.get('adminCount', 0) + 1
        cherrypy.sessions.admin['adminCount'] = adminCount
        
        key = cherrypy.sessions.admin.key
        return self.__examplePage('ram', adminCount, self.samplePages, key)
    
    admin.exposed = True
    
    def forum(self):
        # this function uses its own forum session which is defined in
        # the 
        # the config file "tut10_sessionFilter.conf", otherwise
        # it mirrors the session function
        
        forumCount = cherrypy.sessions.forum.get('forumCount', 0) + 1
        cherrypy.sessions.forum['forumCount'] = forumCount
        
        key = cherrypy.sessions.forum.key
        return self.__examplePage('ram', forumCount, self.samplePages, key)
    
    forum.exposed=True

cherrypy.root = HitCounter()

if __name__ == '__main__':
    cherrypy.config.update(file = "tutorial.conf")
    cherrypy.server.start()

