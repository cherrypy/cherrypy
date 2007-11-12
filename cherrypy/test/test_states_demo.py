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
        # This handler might be called before the engine is STARTED if an
        # HTTP worker thread handles it before the HTTP server returns
        # control to engine.start. We avoid that race condition here
        # by waiting for the Bus to be STARTED.
        cherrypy.engine.block(state=cherrypy.engine.states.STARTED)
        cherrypy.engine.stop()
    stop.exposed = True


if __name__ == '__main__':
    conf = {"server.socket_host": sys.argv[1],
            "server.socket_port": int(sys.argv[2]),
            "log.screen": False,
            "log.error_file": os.path.join(thisdir, 'test_states_demo.error.log'),
            "log.access_file": os.path.join(thisdir, 'test_states_demo.access.log'),
            }
    
    if '-ssl' in sys.argv[3:]:
        localDir = os.path.dirname(__file__)
        serverpem = os.path.join(os.getcwd(), localDir, 'test.pem')
        conf['server.ssl_certificate'] = serverpem
        conf['server.ssl_private_key'] = serverpem
    
    if '-daemonize' in sys.argv[3:]:
        # Sometimes an exception happens during exit;
        # try to make sure we get a non_zero exit code.
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
    
    if '-starterror' in sys.argv[3:]:
        cherrypy.engine.subscribe('start', lambda: 1/0, priority=6)
    
    # This is in a special order for a reason:
    # it allows test_states to wait_for_occupied_port
    # and then immediately call getPage without getting 503.
    cherrypy.config.update(conf)
    cherrypy.tree.mount(Root(), config={'global': conf})
    cherrypy.engine.start()
    cherrypy.engine.block()
