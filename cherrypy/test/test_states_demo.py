import os
import sys
import time
starttime = time.time()

import cherrypy
from cherrypy.restsrv import plugins
thisdir = os.path.join(os.getcwd(), os.path.dirname(__file__))
PID_file_path = os.path.join(thisdir, 'pid_for_test_daemonize')


class Root:
    
    def index(self):
        return "Hello World"
    index.exposed = True
    
    def mtimes(self):
        return repr(cherrypy.engine.publish("Autoreloader", "mtimes"))
    mtimes.exposed = True
    
    def pid(self):
        return str(os.getpid())
    pid.exposed = True
    
    def start(self):
        return repr(starttime)
    start.exposed = True
    
    def stop(self):
        cherrypy.engine.stop()
    stop.exposed = True

if __name__ == '__main__':
    conf = {"server.socket_host": sys.argv[1],
            "server.socket_port": int(sys.argv[2]),
            "log.screen": False,
            }
    
    if '-ssl' in sys.argv[3:]:
        localDir = os.path.dirname(__file__)
        serverpem = os.path.join(os.getcwd(), localDir, 'test.pem')
        conf['server.ssl_certificate'] = serverpem
        conf['server.ssl_private_key'] = serverpem

    if '-daemonize' in sys.argv[3:]:
        # Sometimes an exception happens during exit, try to make sure we get  
        # a non_zero exit code.
        old_exitfunc = sys.exitfunc
        def exitfunc():
            try:
                old_exitfunc()
            except SystemExit:
                raise
            except:
                raise SystemExit(1)
        sys.exitfunc = exitfunc
        
        plugins.Daemonizer(cherrypy.engine).subscribe()
        plugins.PIDFile(cherrypy.engine, PID_file_path).subscribe()
    
    cherrypy.engine.subscribe('start', cherrypy.server.quickstart)   
    
    # This is in a special order for a reason:
    # it allows test_states to wait_for_occupied_port
    # and then immediately call getPage without getting 503.
    try:
        cherrypy.config.update(conf)
        cherrypy.tree.mount(Root(), config={'global': conf})
        cherrypy.engine.start()
        cherrypy.engine.block()
        sys.exit(0)
    except Exception:
        sys.exit(1)
