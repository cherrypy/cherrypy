"""
Copyright (c) 2004, CherryPy Team (team@cherrypy.org)
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

"""Profiler tools for CherryPy.

CherryPy users
==============

You can profile any of your pages as follows:

    from cherrypy.lib import profile
    
    class Root:
        p = profile.Profiler("/path/to/profile/dir")
        
        def index(self):
            self.p.run(self._index)
        index.exposed = True
        
        def _index(self):
            return "Hello, world!"
    
    cherrypy.root = Root()


CherryPy developers
===================

This module can be used whenever you make changes to CherryPy, to get a
quick sanity-check on overall CP performance. Set the config entry:
"profiling.on = True" to turn on profiling. Then, use the serve()
function to browse the results in a web browser. If you run this
module from the command line, it will call serve() for you.

"""


import hotshot
import os, os.path
import sys

try:
    import cStringIO as StringIO
except ImportError:
    import StringIO


class Profiler(object):
    
    def __init__(self, path=None):
        if not path:
            path = os.path.join(os.path.dirname(__file__), "profile")
        self.path = path
        if not os.path.exists(path):
            os.makedirs(path)
        self.count = 0
    
    def run(self, func, *args):
        """run(func, *args). Run func, dumping profile data into self.path."""
        self.count += 1
        path = os.path.join(self.path, "cp_%04d.prof" % self.count)
        prof = hotshot.Profile(path)
        prof.runcall(func, *args)
        prof.close()
    
    def statfiles(self):
        """statfiles() -> list of available profiles."""
        return [f for f in os.listdir(self.path)
                if f.startswith("cp_") and f.endswith(".prof")]
    
    def stats(self, filename, sortby='cumulative'):
        """stats(index) -> output of print_stats() for the given profile."""
        from hotshot.stats import load
        s = load(os.path.join(self.path, filename))
        s.strip_dirs()
        s.sort_stats(sortby)
        oldout = sys.stdout
        try:
            sys.stdout = sio = StringIO.StringIO()
            s.print_stats()
        finally:
            sys.stdout = oldout
        response = sio.getvalue()
        sio.close()
        return response
    
    def index(self):
        return """<html>
        <head><title>CherryPy profile data</title></head>
        <frameset cols='200, 1*'>
            <frame src='menu' />
            <frame name='main' src='' />
        </frameset>
        </html>
        """
    index.exposed = True
    
    def menu(self):
        yield "<h2>Profiling runs</h2>"
        yield "<p>Click on one of the runs below to see profiling data.</p>"
        runs = self.statfiles()
        runs.sort()
        for i in runs:
            yield "<a href='report?filename=%s' target='main'>%s</a><br />" % (i, i)
    menu.exposed = True
    
    def report(self, filename):
        import cherrypy
        cherrypy.response.headerMap['Content-Type'] = 'text/plain'
        return self.stats(filename)
    report.exposed = True


def serve(path=None, port=8080):
    import cherrypy
    cherrypy.root = Profiler(path)
    cherrypy.config.update({'global': {'server.socketPort': port,
                                       'server.threadPool': 10,
                                       'server.environment': "production",
                                       'session.storageType': "ram",
                                       }
                            })
    cherrypy.server.start()


if __name__ == "__main__":
    serve(*tuple(sys.argv[1:]))

