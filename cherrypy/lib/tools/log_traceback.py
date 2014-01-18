import logging

import cherrypy


def log_traceback(severity=logging.ERROR, debug=False):
    """Write the last error's traceback to the cherrypy error log."""
    cherrypy.log("", "HTTP", severity=severity, traceback=True)
