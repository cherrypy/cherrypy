#! /usr/bin/env python
"""The CherryPy daemon."""

import getopt
import sys

import cherrypy
from cherrypy.restsrv import plugins


shortopts = ["d", "e"]
longopts = []

# Help for restd command-line options.
help = """
cherryd. Start the cherrypy daemon.

Usage:
    cherryd <config filename>

"""


def start(options, configfile, *args):
    engine = cherrypy.engine
    
    siteconf = {}
    cherrypy._cpconfig.merge(siteconf, configfile)
    
    cherrypy.config.update(configfile)
    
    if options.has_key('-e'):
        cherrypy.config.update({'environment': options['-e']})
    
    # TODO: Make sure that log files are configurable from the conf file.
    
    # Only daemonize if asked to.
    if options.has_key('-d'):
        # Don't print anything to stdout/sterr.
        cherrypy.config.update({'log.screen': False})
        plugins.Daemonizer(engine).subscribe()
    
    if options.has_key('--pidfile'):
        plugins.PIDFile(engine, options['--pidfile']).subscribe()
    
    cherrypy.signal_handler.subscribe()
    
    # TODO: call a 'site setup' function (probably passing it siteconf).
    
    if options.has_key('--fastcgi'):
        # turn off autoreload when using fastcgi
        cherrypy.config.update({'autoreload.on': False})
        
        cherrypy.server.unsubscribe()
        
        fastcgi_port = cherrypy.config.get('server.socket_port', 4000)
        fastcgi_bindaddr = cherrypy.config.get('server.socket_host', '0.0.0.0')
        bindAddress = (fastcgi_bindaddr, fastcgi_port)
        try:
            # Always start the engine; this will start all other services
            engine.start()
            
            from flup.server.fcgi import WSGIServer
            engine.log('Serving FastCGI on %s:%d' % bindAddress)
            engine.fcgi = WSGIServer(application=wsgiapp,
                                     bindAddress=bindAddress)
            engine.fcgi.run()
            engine.log('FastCGI Server on %s:%d shut down' % bindAddress)
        finally:
            engine.stop()
    else:
        # Always start the engine; this will start all other services
        s = cherrypy.server
        s.httpserver, s.bind_addr = s.httpserver_from_self()
        s.httpserver.wsgi_app = wsgiapp
        engine.start()
        engine.block()


if __name__ == '__main__':
    try:
        opts, args = getopt.getopt(sys.argv[1:], shortopts, longopts)
    except getopt.GetoptError:
        print help
        sys.exit(2)
    
    start(dict(opts), *tuple(args))
