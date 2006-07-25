import os
import sys

import cherrypy


class Root:
    
    def index(self):
        return "Hello World"
    index.exposed = True
    
    def pid(self):
        return str(os.getpid())
    pid.exposed = True
    
    def stop(self):
        cherrypy.engine.stop()
        cherrypy.server.stop()
    stop.exposed = True


if __name__ == '__main__':
    cherrypy.config.update({"server.socket_host": sys.argv[1],
                            "server.socket_port": int(sys.argv[2]),
                            "log_to_screen": False,
                            "environment": "development",
                            })
    cherrypy.quickstart(Root())
 