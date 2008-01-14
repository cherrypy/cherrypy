#! /usr/bin/env python
"""Deployment script for <MyProject> (a CherryPy application).

Run this from the command-line and give it a --config argument:

    python cpdeploy.py --config=example.conf

"""

import os
local_dir = os.path.join(os.getcwd(), os.path.dirname(__file__))

import cherrypy
from cherrypy.restsrv.plugins import Daemonizer, PIDFile

# TODO: Change this to import your project root.
from cherrypy import scaffold


if __name__ == "__main__":
    from optparse import OptionParser
    
    p = OptionParser()
    p.add_option('-c', '--config', dest='config_file',
                 help="specify a config file")
    p.add_option('-D', '--daemonize', action="store_true", dest='daemonize',
                 help="run the server as a daemon")
    options, args = p.parse_args()
    cherrypy.config.update(options.config_file)
    
    # Only daemonize if asked to.
    if options.daemonize:
        # Don't print anything to stdout/sterr.
        cherrypy.config.update({'log.screen': False})
        
        d = Daemonizer(cherrypy.engine)
        d.subscribe()
    
    pidfile = cherrypy.config.get('pidfile')
    if pidfile:
        PIDFile(cherrypy.engine, pidfile).subscribe()
    
    # You can replace the next 4 lines with:
    # cherrypy.quickstart(scaffold.root, "/", options.config_file)
    cherrypy.signal_handler.subscribe()
    cherrypy.tree.mount(scaffold.root, "/", options.config_file)
    cherrypy.engine.start()
    cherrypy.engine.block()

