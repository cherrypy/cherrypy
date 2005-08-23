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
import cgi
import urllib
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

# Guess initial depth to hide FIXME this doesn't work for non-cherrypy stuff
import cherrypy
initial_base = os.path.dirname(cherrypy.__file__)

TEMPLATE_MENU = """<html>
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
        .pass {color: #888;}
        #pct {text-align: right;}
        h3 { font-size: small; font-weight: bold; font-style: italic; margin-top: 5px;}
        input { border: 1px solid #ccc; padding: 2px; }
    </style>
</head>
<body>
<h2>CherryPy Coverage</h2>"""

TEMPLATE_FORM = """
<form action='menu' method=GET>
    <input type='hidden' name='base' value='%(base)s' />
    <h3>Options</h3>
    <input type='checkbox' %(showpct)s name='showpct' value='checked'/>
    show percentages <br />
    Hide files over <input type='text' id='pct' name='pct' value='%(pct)s' size='3' />%%<br />
    Exclude files matching<br />
    <input type='text' id='exclude' name='exclude' value='%(exclude)s' size='20' />
    <br />

    <input type='submit' value='Change view' />
</form>""" 

TEMPLATE_FRAMESET = """<html>
<head><title>CherryPy coverage data</title></head>
<frameset cols='250, 1*'>
    <frame src='menu?base=%s' />
    <frame name='main' src='' />
</frameset>
</html>
""" % initial_base.lower()

TEMPLATE_COVERAGE = """<html>
<head>
    <title>Coverage for %(name)s</title>
    <style>
        h2 { margin-bottom: .25em; }
        p { margin: .25em; }
        .covered { color: #000; background-color: #fff; }
        .notcovered { color: #fee; background-color: #500; }
        .excluded { color: #00f; background-color: #fff; }
         table .covered, table .notcovered, table .excluded
             { font-family: Andale Mono, monospace;
               font-size: 10pt; white-space: pre; }

         .lineno { background-color: #eee;}
         .notcovered .lineno { background-color: #000;}
         table { border-collapse: collapse;
    </style>
</head>
<body>
<h2>%(name)s</h2>
<p>%(fullpath)s</p>
<p>Coverage: %(pc)s%%</p>"""

TEMPLATE_LOC_COVERED = """<tr class="covered">
    <td class="lineno">%s&nbsp;</td>
    <td>%s</td>
</tr>\n"""
TEMPLATE_LOC_NOT_COVERED = """<tr class="notcovered">
    <td class="lineno">%s&nbsp;</td>
    <td>%s</td>
</tr>\n"""
TEMPLATE_LOC_EXCLUDED = """<tr class="excluded">
    <td class="lineno">%s&nbsp;</td>
    <td>%s</td>
</tr>\n"""


def _skip_file(path, exclude):
    if exclude:
        return bool(re.search(exclude, path))

def _percent(statements, missing):
    s = len(statements)
    e = s - len(missing)
    if s > 0:
        return int(round(100.0 * e / s))
    return 0

def _show_branch(root, base="", path="", pct=0, showpct=False, exclude=""):
    
    # Show the directory name and any of our children
    dirs = [k for k, v in root.iteritems() if v is not None]
    dirs.sort()
    for name in dirs:
        if path:
            newpath = os.sep.join((path, name))
        else:
            newpath = name
        
        if newpath.startswith(base):
            relpath = newpath[len(base):]
            yield "<nobr>" + ("|&nbsp;" * relpath.count(os.sep)) + "<b>"
            yield ("<a href='menu?base=%s&exclude=%s'>%s</a>" %
                   (newpath, urllib.quote_plus(exclude), name))
            yield "</b></nobr><br />\n"
        
        for chunk in _show_branch(root[name], base, newpath, pct, showpct, exclude):
            yield chunk
    
    # Now list the files
    if path.startswith(base):
        relpath = path[len(base):]
        files = [k for k, v in root.iteritems() if v is None]
        files.sort()
        for name in files:
            if path:
                newpath = os.sep.join((path, name))
            else:
                newpath = name
            
            pc_str = ""
            if showpct:
                try:
                    _, statements, _, missing, _ = coverage.analysis2(newpath)
                except:
                    # Yes, we really want to pass on all errors.
                    pass
                else:
                    pc = _percent(statements, missing)
                    pc_str = ("%3d%% " % pc).replace(' ','&nbsp;')
                    if pc < float(pct) or pc == -1:
                        pc_str = "<span class='fail'>%s</span>" % pc_str
                    else:
                        pc_str = "<span class='pass'>%s</span>" % pc_str
            
            yield ("<nobr>%s%s<a href='report?name=%s' target='main'>%s</a></nobr><br />\n"
                   % ("|&nbsp;" * (relpath.count(os.sep) + 1), pc_str, newpath, name))

def get_tree(base, exclude):
    """Return covered module names as a nested dict."""
    tree = {}
    coverage.get_ready()
    runs = coverage.cexecuted.keys()
    if runs:
        tree = {}
        def graft(path):
            head, tail = os.path.split(path)
            if tail:
                return graft(head).setdefault(tail, {})
            else:
                return tree.setdefault(head.strip(r"\/"), {})
        
        for path in runs:
            if not _skip_file(path, exclude) and not os.path.isdir(path):
                head, tail = os.path.split(path)
                if head.startswith(base):
                    graft(head)[tail] = None
    return tree


class CoverStats(object):
    
    def index(self):
        return TEMPLATE_FRAMESET
    index.exposed = True
    
    def menu(self, base="", pct="50", showpct="",
             exclude=r'python\d\.\d|test|tut\d|tutorial'):
        
        # The coverage module uses all-lower-case names.
        base = base.lower().rstrip(os.sep)
        
        yield TEMPLATE_MENU
        yield TEMPLATE_FORM % locals()
        
        yield "<div id='tree'>"
        
        # Start by showing links for parent paths
        path = ""
        atoms = base.split(os.sep)
        atoms.pop()
        for atom in atoms:
            path += atom + os.sep
            yield ("<nobr><b><a href='menu?base=%s&exclude=%s'>%s</a></b></nobr>%s\n"
                   % (path, urllib.quote_plus(exclude), atom, os.sep))
        
        tree = get_tree(base, exclude)
        if not tree:
            yield "<p>No modules covered.</p>"
        else:
            # Now show all visible branches
            yield "<br />"
            for chunk in _show_branch(tree, base, "", pct, showpct=='checked', exclude):
                yield chunk
        
        yield "</div>"
        yield "</body></html>"
    menu.exposed = True
    
    def annotated_file(self, filename, statements, excluded, missing):
        source = open(filename, 'r')
        lineno = 0
        while 1:
            line = source.readline()
            if line == '':
                break
            line = line[:-1]
            lineno = lineno + 1
            if line == '':
                yield '&nbsp;'
                continue
            if lineno in excluded:
                template = TEMPLATE_LOC_EXCLUDED
            elif lineno in missing:
                template = TEMPLATE_LOC_NOT_COVERED
            else:
                template = TEMPLATE_LOC_COVERED
            yield template % (lineno, cgi.escape(line))
    
    def report(self, name):
        coverage.get_ready()
        filename, statements, excluded, missing, _ = coverage.analysis2(name)
        pc = _percent(statements, missing)
        yield TEMPLATE_COVERAGE % dict(name=os.path.basename(name),
                                       fullpath=name,
                                       pc=pc)
        yield '<table>\n'
        for line in self.annotated_file(filename, statements, excluded,
                                        missing):
            yield line
        yield '</table>'
        yield '</body>'
        yield '</html>'
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

