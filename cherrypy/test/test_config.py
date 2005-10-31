"""
Copyright (c) 2005, CherryPy Team (team@cherrypy.org)
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, 
are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice, 
      this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice, 
      this list of conditions and the following disclaimer in the documentation 
      and/or other materials provided with the distribution.
    * Neither the name of the CherryPy Team nor the names of its contributors 
      may be used to endorse or promote products derived from this software 
      without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND 
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED 
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE 
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE 
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL 
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR 
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER 
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, 
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE 
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

"""Tests for the CherryPy configuration system."""

import cherrypy

class Root:
    def index(self, key):
        return cherrypy.config.get(key, "None")
    index.exposed = True
    _global = index
    xyz = index

class Foo:
    def index(self, key):
        return cherrypy.config.get(key, "None")
    index.exposed = True
    bar = index
    nex = index

class Env:
    def index(self, key):
        return str(cherrypy.config.get(key, "None"))
    index.exposed = True
    prod = index

cherrypy.root = Root()
cherrypy.root.foo = Foo()
cherrypy.root.env = Env()
cherrypy.config.update({
    'global': {'server.logToScreen': False,
               'server.environment': 'production',
               'server.showTracebacks': True,
               'server.protocolVersion': "HTTP/1.1",
               },
    '/': {
        'foo': 'this',
        'bar': 'that',
        },
    '/foo': {
        'foo': 'this2',
        'baz': 'that2',
        },
    '/foo/bar': {
        'foo': 'this3',
        'bax': 'this4',
        },
    '/env': {'server.environment': 'development'},
    '/env/prod': {'server.environment': 'production'},
})

# Shortcut syntax--should get put in the "global" bucket
cherrypy.config.update({'luxuryyacht': 'throatwobblermangrove'})

import helper

class ConfigTests(helper.CPWebCase):
    
    def testConfig(self):
        tests = [
            ('*',        'luxuryyacht', 'throatwobblermangrove'),
            ('/',        'nex', 'None'),
            ('/',        'foo', 'this'),
            ('/',        'bar', 'that'),
            ('/xyz',     'foo', 'this'),
            ('/foo/',    'foo', 'this2'),
            ('/foo/',    'bar', 'that'),
            ('/foo/',    'bax', 'None'),
            ('/foo/bar', 'baz', 'that2'),
            ('/foo/nex', 'baz', 'that2'),
        ]
        for path, key, expected in tests:
            self.getPage(path + "?key=" + key)
            self.assertBody(expected)
    
    def testEnvironments(self):
        for key, val in cherrypy.config.environments['development'].iteritems():
            self.getPage("/env/?key=" + key)
            # The dev environment will have logdebuginfo data
            self.assertEqual(self.body.split("\n")[0], str(val))
        for key, val in cherrypy.config.environments['production'].iteritems():
            self.getPage("/env/prod/?key=" + key)
            self.assertBody(str(val))


if __name__ == '__main__':
    helper.testmain()
