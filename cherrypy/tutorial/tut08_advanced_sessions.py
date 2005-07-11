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
                'global' : { 'sessionFilter.on': True},
                '/admin' : { 'sessionFilter.admin.on' : True },
                '/forum' : { 'sessionFilter.forum.on' : True }
                })

    # this is just a primative template function
    def __examplePage(self, poweredBy, count, links, sessionKey, cookieName):
        yield '<html><head><title>sessionFilter example</title><body>\n'
        yield 'This page uses %s based session storage.<br/>\n' % poweredBy
        yield 'You have viewed this page %i times. <br/><br/>\n' % count
        for link in links:
            yield '<a href="/%s">%s</a>&nbsp;&nbsp;\n' % (link, link)

        yield '<br/><br/>The Current session key is: &nbsp;&nbsp;\n'
        yield sessionKey
        yield '<br/>The Current cookie name is: &nbsp;&nbsp;\n'
        yield cookieName
        yield '\n</body></html>'

    # a list of the pages used in the example so we can add pages
    # without changing any code
    samplePages = ['admin', 'index', 'forum']
    
    def index(self):
        # this function uses the default session
        # it may not be the defualt in future versions
        
        # Increase the silly hit counter
        count = cherrypy.session.get('count', 0) + 1

        # Store the new value in the session dictionary
        # cherrypy.session is available by default
        cherrypy.session['count'] = count

        # And display a silly hit count message!
        # cherrypy.session is an alias to cherrypy.session.default
        # it allows dictionary functionality but the attributes
        # must be accessed through cherrypy.session.default
        key = cherrypy.session.default.key
        cookieName = cherrypy.session.default.cookieName
        return self.__examplePage('ram', count, self.samplePages, key, cookieName)

    index.exposed = True

    def admin(self):
        # this function uses the admin which is defined in
        # the config file "tut10_sessionFilter.conf", otherwise
        # it mirrors the session function

        adminCount = cherrypy.session.admin.get('adminCount', 0) + 1
        cherrypy.session.admin['adminCount'] = adminCount
        
        key = cherrypy.session.admin.key
        cookieName = cherrypy.session.admin.cookieName
        return self.__examplePage('ram', adminCount, self.samplePages, key, cookieName)
    
    admin.exposed = True
    
    def forum(self):
        # this function uses its own forum session which is defined in
        # the 
        # the config file "tut10_sessionFilter.conf", otherwise
        # it mirrors the session function
        
        forumCount = cherrypy.session.forum.get('forumCount', 0) + 1
        cherrypy.session.forum['forumCount'] = forumCount
        
        key = cherrypy.session.forum.key

        cookieName = cherrypy.session.forum.cookieName
        return self.__examplePage('ram', forumCount, self.samplePages, key, cookieName)
    
    forum.exposed=True

cherrypy.root = HitCounter()

if __name__ == '__main__':
    cherrypy.config.update(file = "tutorial.conf")
    cherrypy.server.start()

