from cherrypy import cpg

class HelloWorld:
    def index(self):
        return "Hello world!"
    index.exposed = True
    wsgi_asp = index

cpg.root = HelloWorld()
cpg.root.test = HelloWorld()

cpg.config.update({"global": {"server.environment": "production",
                              "session.storageType": "ram"}})
cpg.server.start(initOnly = True)

