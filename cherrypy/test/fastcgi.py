import cherrypy
from cherrypy.process import plugins, servers
from cherrypy.test import test_caching

if hasattr(test_caching, 'setup_server'):
    test_caching.setup_server()

def run():
    cherrypy.config.update('C:\\Python25\\Lib\\site-packages\\cherrypy\\test\\test.conf')
    
    engine = cherrypy.engine
    cherrypy.config.update({'environment': 'test_suite'})
    
    if hasattr(engine, "signal_handler"):
        engine.signal_handler.subscribe()
    if hasattr(engine, "console_control_handler"):
        engine.console_control_handler.subscribe()
    
    # Turn off autoreload when using fastcgi.
    cherrypy.config.update({'engine.autoreload_on': False})
    cherrypy.server.unsubscribe()
    bindAddress = ('127.0.0.1', 4000)
    f = servers.FlupFCGIServer(application=cherrypy.tree, bindAddress=bindAddress)
    s = servers.ServerAdapter(engine, httpserver=f, bind_addr=bindAddress)
    s.subscribe()
    
    # Always start the engine; this will start all other services
    try:
        engine.start()
    except:
        # Assume the error has been logged already via bus.log.
        sys.exit(1)
    else:
        engine.block()

if __name__ == '__main__':
    run()
