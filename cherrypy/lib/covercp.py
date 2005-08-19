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

"""Code-coverage tools for CherryPy.

To use this module, or the coverage tools in the test suite,
you need to download 'coverage.py', either Gareth Rees' original
implementation:
http://www.garethrees.org/2001/12/04/python-coverage/

or Ned Batchelder's enhanced version:
http://www.nedbatchelder.com/code/modules/coverage.html

Set "cherrypy.codecoverage = True" to turn on coverage tracing.
Then, use the serve() function to browse the results in a web browser.
If you run this module from the command line, it will call serve() for you.
"""

import re
import sys
import os, os.path
localFile = os.path.join(os.path.dirname(__file__), "coverage.cache")

try:
    import cStringIO as StringIO
except ImportError:
    import StringIO


try:
    from coverage import the_coverage as coverage
    def start():
        coverage.start()
except ImportError:
    # Setting coverage to None will raise errors
    # that need to be trapped downstream.
    coverage = None
    
    import warnings
    warnings.warn("No code coverage will be performed; coverage.py could not be imported.")
    
    def start():
        pass


class CoverStats(object):
    
    def index(self):
        return """<html>
        <head><title>CherryPy coverage data</title></head>
        <frameset cols='250, 1*'>
            <frame src='menu' />
            <frame name='main' src='' />
        </frameset>
        </html>
        """
    index.exposed = True
    
    def menu(self, base="", pct=""):
        yield """<html>
<head>
    <title>CherryPy Coverage Menu</title>
    <style>
        body {font: 9pt Arial, serif;}
        #tree {font: 8pt Courier, sans-serif;}
        #tree a:active, a:focus {
            background-color: #EEEEFF;
            padding: 1px;
            border: 1px solid #9999FF;
            -moz-outline-style: none;
        }
        .fail {color: red;}
        #pct {text-align: right;}
    </style>
</head>
<body>
<h2>CherryPy Coverage</h2>"""
        
        coverage.get_ready()
        runs = coverage.cexecuted.keys()
        if runs:
            yield """<form action='menu'>
    <input type='hidden' name='base' value='%s' />
    <input type='submit' value='Show %%' />
    threshold: <input type='text' id='pct' name='pct' value='%s' size='3' />%%
</form>""" % (base, pct or "50")
            
            yield "<div id='tree'>"
            tree = {}
            def graft(path):
                b, n = os.path.split(path)
                if n:
                    return graft(b).setdefault(n, {})
                else:
                    return tree.setdefault(b.strip(r"\/"), {})
            for path in runs:
                if not os.path.isdir(path):
                    b, n = os.path.split(path)
                    if b.startswith(base):
                        graft(b)[n] = None
            
            def show(root, depth=0, path=""):
                dirs = [k for k, v in root.iteritems() if v is not None]
                dirs.sort()
                for name in dirs:
                    if path:
                        newpath = os.sep.join((path, name))
                    else:
                        newpath = name
                    
                    yield "<nobr>" + ("|&nbsp;" * depth) + "<b>"
                    yield "<a href='menu?base=%s'>%s</a>" % (newpath, name)
                    yield "</b></nobr><br />\n"
                    for chunk in show(root[name], depth + 1, newpath):
                        yield chunk
                
                files = [k for k, v in root.iteritems() if v is None]
                files.sort()
                for name in files:
                    if path:
                        newpath = os.sep.join((path, name))
                    else:
                        newpath = name
                    
                    pc_str = ""
                    if pct:
                        try:
                            _, statements, _, missing, _ = coverage.analysis2(newpath)
                        except:
                            # Yes, we really want to pass on all errors.
                            pass
                        else:
                            s = len(statements)
                            e = s - len(missing)
                            if s > 0:
                                pc = 100.0 * e / s
                                pc_str = "%d%% " % pc
                                if pc < 100:
                                    pc_str = "&nbsp;" + pc_str
                                    if pc < 10:
                                        pc_str = "&nbsp;" + pc_str
                                if pc < float(pct):
                                    pc_str = "<span class='fail'>%s</span>" % pc_str
                    yield ("<nobr>%s%s<a href='report?name=%s' target='main'>%s</a></nobr><br />\n"
                           % ("|&nbsp;" * depth, pc_str, newpath, name))
            
            for chunk in show(tree):
                yield chunk
            
            yield "</div>"
        else:
            yield "<p>No modules covered.</p>"
        yield "</body></html>"
    menu.exposed = True
    
    def annotated_file(self, filename, statements, excluded, missing):
        source = open(filename, 'r')
        dest = StringIO.StringIO()
        lineno = 0
        i = 0
        j = 0
        covered = 1
        while 1:
            line = source.readline()
            if line == '':
                break
            lineno = lineno + 1
            while i < len(statements) and statements[i] < lineno:
                i = i + 1
            while j < len(missing) and missing[j] < lineno:
                j = j + 1
            if i < len(statements) and statements[i] == lineno:
                covered = j >= len(missing) or missing[j] > lineno
            if coverage.blank_re.match(line):
                dest.write('  ')
            elif coverage.else_re.match(line):
                # Special logic for lines containing only
                # 'else:'.  See [GDR 2001-12-04b, 3.2].
                if i >= len(statements) and j >= len(missing):
                    dest.write('! ')
                elif i >= len(statements) or j >= len(missing):
                    dest.write('> ')
                elif statements[i] == missing[j]:
                    dest.write('! ')
                else:
                    dest.write('> ')
            elif lineno in excluded:
                dest.write('- ')
            elif covered:
                dest.write('> ')
            else:
                dest.write('! ')
            dest.write(line)
        source.close()
        result = dest.getvalue()
        dest.close()
        return result
    
    def report(self, name):
        import cherrypy
        cherrypy.response.headerMap['Content-Type'] = 'text/plain'
        
        yield name
        yield "\n"
        
        coverage.get_ready()
        filename, statements, excluded, missing, _ = coverage.analysis2(name)
        s = len(statements)
        e = s - len(missing)
        if s > 0:
            pc = 100.0 * e / s
            yield "%2d%% covered\n" % pc
        
        yield "\n"
        yield self.annotated_file(filename, statements, excluded, missing)
    report.exposed = True


def serve(path=localFile, port=8080):
    if coverage is None:
        raise ImportError("<p>The coverage module could not be imported.</p>")
    coverage.cache_default = path
    
    import cherrypy
    cherrypy.root = CoverStats()
    cherrypy.config.update({'server.socketPort': port,
                            'server.threadPool': 10,
                            'server.environment': "production",
                            })
    cherrypy.server.start()


if __name__ == "__main__":
    serve(*tuple(sys.argv[1:]))

