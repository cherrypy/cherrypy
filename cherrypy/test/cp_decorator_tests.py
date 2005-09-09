
import cherrypy
class Exposing:
    @cherrypy.expose("1")
    def base(self):
        return "expose works!"
    cherrypy.expose(base, "2")

class ExposingNewStyle(object):
    @cherrypy.expose("1")
    def base(self):
        return "expose works!"
    cherrypy.expose(base, "2")
