from cherrypy.test import test
test.prefer_parent_path()

import cherrypy


def setup_server():
    
    class ClassOfRoot(object):
        
        def __init__(self, name):
            self.name = name
        
        def index(self):
            return "Welcome to the %s website!" % self.name
        index.exposed = True
    
    
    cherrypy.config.update({'environment': 'test_suite'})
    
    default = cherrypy.Application(None)
    
    domains = {}
    for year in xrange(1997, 2008):
        app = cherrypy.Application(ClassOfRoot('Class of %s' % year))
        domains['www.classof%s.example' % year] = app
    
    cherrypy.tree.graft(cherrypy._cpwsgi.VirtualHost(default, domains))


from cherrypy.test import helper


class WSGI_VirtualHost_Test(helper.CPWebCase):
    
    def test_welcome(self):
        for year in xrange(1997, 2008):
            self.getPage("/", headers=[('Host', 'www.classof%s.example' % year)])
            self.assertBody("Welcome to the Class of %s website!" % year)


if __name__ == '__main__':
    setup_server()
    helper.testmain()

