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
    def __examplePage(self, poweredBy, count, links, sessionKey):
        yield '<html><head><title>sessionFilter exampe</title><body>\n'
        yield 'This page uses %s based session storage.<br/>\n' % poweredBy
        yield 'You have viewed this page %i times. <br/><br/>\n' % count
        for link in links:
            yield '<a href="/%s">%s</a>&nbsp;&nbsp;\n' % (link, link)

        yield '<br/><br/>The Current SessionKey is: &nbsp;&nbsp;\n'
        yield sessionKey
        yield '\n</body></html>'

    samplePages = ['admin', 'index', 'forum', 'sqlobject']

    def admin(self):
        adminCount = cpg.sessions.adminSession.get('adminCount', 0) + 1
        cpg.sessions.adminSession['adminCount'] = adminCount
        
        key = cpg.sessions.adminSession.key
        return self.__examplePage('ram', adminCount, self.samplePages, key)

    admin.exposed = True
    
    def forum(self):
        forumCount = cpg.sessions.forumSession.get('forumCount', 0) + 1
        cpg.sessions.forumSession['forumCount'] = forumCount
        
        key = cpg.sessions.forumSession.key
        return self.__examplePage('ram', forumCount, self.samplePages, key)
    forum.exposed=True

    def index(self):
        # Increase the silly hit counter
        count = cpg.sessions.sessionMap.get('count', 0) + 1

        # Store the new value in the session dictionary
        cpg.sessions.sessionMap['count'] = count

        # And display a silly hit count message!
        key = cpg.sessions.sessionMap.key
        return self.__examplePage('ram', count, self.samplePages, key)

    index.exposed = True

cpg.root = HitCounter()

cpg.config.update(file = 'tut10_sessionfilter.conf')
cpg.server.start()
