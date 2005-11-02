"""Test WSGI servers and gateways, such as mod_python.

mod_python
----------

Put the following four lines somewhere in your Apache2 .conf:

PythonImport cherrypy.test.test_noserver REDROVER.HQAMOR.amorhq.net
SetHandler python-program
PythonHandler wsgiref.modpython_gateway::handler
PythonOption application cherrypy._cpwsgi::wsgiApp

"""
import test
test.prefer_parent_path()

import cherrypy
from cherrypy import _cpwsgi

class HelloWorld:
    def index(self):
        return "Hello world!"
    index.exposed = True
    wsgi_asp = index

cherrypy.root = HelloWorld()
cherrypy.root.test = HelloWorld()

cherrypy.config.update({"server.environment": "production"})
cherrypy.server.start(serverClass=None)

