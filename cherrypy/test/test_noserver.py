import cherrypy

class HelloWorld:
    def index(self):
        return "Hello world!"
    index.exposed = True
    wsgi_asp = index

cherrypy.root = HelloWorld()
cherrypy.root.test = HelloWorld()

cherrypy.config.update({"global": {"server.environment": "production",
                              "session.storageType": "ram"}})
cherrypy.server.start(initOnly = True)

